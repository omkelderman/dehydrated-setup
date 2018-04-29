from abc import ABC, abstractmethod
import CloudFlare
from transip.service.domain import DomainService
from transip.service.objects import DnsEntry
import sys
from time import sleep
import subprocess
import yaml

def load_config():
    with open('/etc/dehydrated/dns-config.yml', 'r') as stream:
        return yaml.safe_load(stream)
CONFIG = load_config()

class AcmeDnsClient(ABC):
    def __init__(self, authoritative_name_server):
        self.authoritative_name_server = authoritative_name_server
        self.names_added = []

    def queue_add(self, domain, name, challenge):
        full_name = self.to_dns_name(name)
        self.names_added.append((full_name, challenge))
        self._queue_add(domain, full_name, challenge)

    @abstractmethod
    def _queue_add(self, domain, name, challenge):
        pass

    def queue_delete(self, domain, name, challenge):
        self._queue_delete(domain, self.to_dns_name(name), challenge)

    @abstractmethod
    def _queue_delete(self, domain, name, challenge):
        pass

    @abstractmethod
    def execute(self):
        pass

    def to_dns_name(self, name):
        return '_acme-challenge.'+name

    def wait_for_add_propagated(self):
        if len(self.names_added) == 0:
            return

        print('check if records have been propagated on %s' % self.authoritative_name_server)
        for entry in self.names_added:
            while True:
                domain, challenge = entry
                exists = self.check_domain_has_propagated(domain, challenge)
                if exists:
                    # yay, we found it, lets continue to next one and break out of the check look
                    print('TXT record "%s" has been found for %s' % (challenge, domain))
                    break
                else:
                    print('TXT record "%s" for %s has not been found yet, waiting %d sec and trying again...' % (challenge, domain, CONFIG['sleep']['retry']))
                    sleep(CONFIG['sleep']['retry'])

    def check_domain_has_propagated(self, domain, challenge):
        dns_result = subprocess.check_output(['dig', '+short', 'TXT', domain, '@'+self.authoritative_name_server], universal_newlines=True)
        return ('"%s"' % challenge) in dns_result.split('\n')


class CloudflareAcmeDnsClient(AcmeDnsClient):
    def __init__(self, config):
        super().__init__(config['nameserver'])
        self.zone_ids = {}
        self.dns_records_for_zone_cache = {}
        self.add_queue = []
        self.remove_queue = []
        self.cf = CloudFlare.CloudFlare(email=config['email'], token=config['token'])

    def get_zone_id(self, domain):
        if domain in self.zone_ids:
            return self.zone_ids[domain]
        else:
            zone_id = self.cf.zones.get(params={'name':domain})[0]['id']
            self.zone_ids[domain] = zone_id
            return zone_id

    def get_all_dns_records_for_zone(self, zone_id):
        if zone_id in self.dns_records_for_zone_cache:
            return self.dns_records_for_zone_cache[zone_id]
        else:
            records = self.cf.zones.dns_records.get(zone_id)
            self.dns_records_for_zone_cache[zone_id] = records
            return records

    def _queue_add(self, domain, name, challenge):
        zone_id = self.get_zone_id(domain)
        self.add_queue.append({'zone_id': zone_id, 'data':{'name':name, 'type':'TXT', 'content':challenge}})

    def _queue_delete(self, domain, name, challenge):
        zone_id = self.get_zone_id(domain)
        for record in self.get_all_dns_records_for_zone(zone_id):
            if record['type'] == 'TXT' and record['name'] == name and record['content'] == challenge:
                self.remove_queue.append({'zone_id': zone_id, 'record_id': record['id']})
                break

    def execute(self):
        for a in self.add_queue:
            self.cf.zones.dns_records.post(a['zone_id'], data=a['data'])
        for d in self.remove_queue:
            self.cf.zones.dns_records.delete(d['zone_id'], d['record_id'])


class TransIpAcmeDnsClient(AcmeDnsClient):
    def __init__(self, config):
        super().__init__(config['nameserver'])
        self.tid = DomainService(config['username'], config['key-file'])
        self.dns_records = {}

    def load_domain(self, domain):
        if domain in self.dns_records:
            return

        self.dns_records[domain] = self.tid.get_info(domain).dnsEntries

    def build_record(self, domain, name, challenge):
        return DnsEntry(name[:-(len(domain)+1)], 1, DnsEntry.TYPE_TXT, challenge)

    def _queue_add(self, domain, name, challenge):
        self.load_domain(domain)
        record = self.build_record(domain, name, challenge)
        if record in self.dns_records[domain]:
            raise Exception('record already exists for %s -> %s' % (name, challenge))

        self.dns_records[domain].append(record)

    def _queue_delete(self, domain, name, challenge):
        self.load_domain(domain)
        record = self.build_record(domain, name, challenge)

        try:
            self.dns_records[domain].remove(record)
        except ValueError:
            pass

    def execute(self):
        for domain in self.dns_records:
            self.tid.set_dns_entries(domain, self.dns_records[domain])


PROVIDERS = {
    'transip': TransIpAcmeDnsClient(CONFIG['transip']),
    'cloudflare': CloudflareAcmeDnsClient(CONFIG['cloudflare'])
}

def get_profider(name):
    for d in CONFIG['domains']:
        if name.endswith(d):
            return (d, PROVIDERS[CONFIG['domains'][d]])

    raise ValueError('domain not found :(')

if __name__ == '__main__':
    if len(sys.argv) < 2 or (sys.argv[1] != 'deploy_challenge' and sys.argv[1] != 'clean_challenge') or ((len(sys.argv)-2)%3)!=0 :
        print('%s <deploy_challenge|clean_challenge> [<domain> <ignored> <challenge>] [...]' % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    add = sys.argv[1] == 'deploy_challenge'

    for i in range(2, len(sys.argv), 3):
        name = sys.argv[i]
        challenge = sys.argv[i+2]
        domain, provider = get_profider(name)
        if add:
            provider.queue_add(domain, name, challenge)
        else:
            provider.queue_delete(domain, name, challenge)

    for p in PROVIDERS:
        PROVIDERS[p].execute()

    if add:
        print('Sleeping for %d seconds to give a little bit of time for records to propagate' % CONFIG['sleep']['initial'])
        sleep(CONFIG['sleep']['initial'])
        for p in PROVIDERS:
            PROVIDERS[p].wait_for_add_propagated()

