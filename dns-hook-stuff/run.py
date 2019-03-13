from abc import ABC, abstractmethod
import CloudFlare
from transip.service.domain import DomainService as TransIpDomainService
from transip.service.objects import DnsEntry as TransIpDnsEntry
import sys
from time import sleep
import subprocess
import yaml
import requests

def load_config():
    with open('/etc/dehydrated/dns-config.yml', 'r') as stream:
        return yaml.safe_load(stream)
CONFIG = load_config()

class AcmeDnsClient(ABC):
    def __init__(self, authoritative_name_servers):
        self.authoritative_name_servers = authoritative_name_servers
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

        print('check if records have been propagated on %s' % ', '.join(self.authoritative_name_servers))
        retry_seconds = CONFIG['sleep']['retry']
        max_retries = CONFIG['sleep']['max-retries']
        for entry in self.names_added:
            count = 0
            while True:
                domain, challenge = entry
                exists = self.check_domain_has_propagated(domain, challenge)
                if exists:
                    # yay, we found it, lets continue to next one and break out of the check look
                    print('TXT record "%s" for %s has been seen on all authoritative nameservers!' % (challenge, domain))
                    break
                else:
                    if count >= max_retries:
                        print('TXT record "%s" for %s is not seen on all authoritative nameservers yet, max retries has been reached. Adding failed!' % (challenge, domain))
                        return False

                    print('TXT record "%s" for %s is not seen on all authoritative nameservers yet, waiting %d sec and trying again...' % (challenge, domain, retry_seconds))
                    sleep(retry_seconds)
                    count += 1

        return True

    def check_domain_has_propagated(self, domain, challenge):
        for auth_name_server in self.authoritative_name_servers:
            dns_result = subprocess.check_output(['dig', '+short', 'TXT', domain, '@'+auth_name_server], universal_newlines=True)
            if not ('"%s"' % challenge) in dns_result.split('\n'):
                return False
        return True

class CloudflareAcmeDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config):
        super().__init__(authoritative_name_servers)
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
    def __init__(self, authoritative_name_servers, config):
        super().__init__(authoritative_name_servers)
        self.tid = TransIpDomainService(config['username'], config['key-file'])
        self.dns_records = {}

    def load_domain(self, domain):
        if domain in self.dns_records:
            return

        self.dns_records[domain] = self.tid.get_info(domain).dnsEntries

    def build_record(self, domain, name, challenge):
        return TransIpDnsEntry(name[:-(len(domain)+1)], 1, TransIpDnsEntry.TYPE_TXT, challenge)

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

class DigitalOceanDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config):
        super().__init__(authoritative_name_servers)
        self.custom_api_request_headers = {'Authorization': 'Bearer ' + config['bearer-token']}
        self.dns_records_for_domain_cache = {}
        self.add_queue = []    # {domain: xxx, name: subdomain or @, data: challenge}
        self.remove_queue = [] # {domain: xxx, record_id: 123}

    def get_subdomain_part(self, domain, fulldomain):
        if domain == fulldomain:
            # its the base domain self, which is represented by a '@'
            return '@'

        dotDomain = '.' + domain
        if fulldomain.endswith(dotDomain):
            # detected valid subdomain
            return fulldomain[:-len(dotDomain)]

        # no subdomain detected
        raise ValueError('fulldomain not a subdomain of domain')

    def _queue_add(self, domain, name, challenge):
        subdomain = self.get_subdomain_part(domain, name)
        self.add_queue.append({'domain': domain, 'name': subdomain, 'data': challenge})

    def get_all_dns_records_for_domain(self, domain):
        if domain in self.dns_records_for_domain_cache:
            return self.dns_records_for_domain_cache[domain]
        else:
            records = self.fetch_all_dns_records_for_domain(domain)
            self.dns_records_for_domain_cache[domain] = records
            return records

    def _queue_delete(self, domain, name, challenge):
        subdomain = self.get_subdomain_part(domain, name)
        for record in self.get_all_dns_records_for_domain(domain):
            if record['type'] == 'TXT' and record['name'] == subdomain and record['data'] == challenge:
                self.remove_queue.append({'domain': domain, 'record_id': record['id']})
                break

    def execute(self):
        for a in self.add_queue:
            self.add_txt_dns_record(a['domain'], a['name'], a['data'])
        for d in self.remove_queue:
            self.remove_dns_record(d['domain'], d['record_id'])

    # All the API call functionality
    def fetch_all_dns_records_for_domain(self, domain):
        result = []
        url = 'https://api.digitalocean.com/v2/domains/%s/records?per_page=200' % domain

        while True:
            r = requests.get(url, headers=self.custom_api_request_headers)
            if r.status_code != 200:
                raise ValueError('error retrieving dns records')
            json_data = r.json()
            for record in json_data['domain_records']:
                result.append(record)
            if 'pages' in json_data['links'] and 'next' in json_data['links']['pages']:
                url = json_data['links']['pages']['next']
            else:
                break
        
        return result
    
    def add_txt_dns_record(self, domain, name, data):
        data = {'type': 'TXT', 'name': name, 'data': data, 'ttl': 60}
        r = requests.post('https://api.digitalocean.com/v2/domains/%s/records' % domain, json=data, headers=self.custom_api_request_headers)
        if r.status_code != 201:
            raise ValueError('error while creating new dns txt record')

    def remove_dns_record(self, domain, record_id):
        r = requests.delete('https://api.digitalocean.com/v2/domains/%s/records/%d' % (domain, record_id), headers=self.custom_api_request_headers)
        if r.status_code != 204:
            raise ValueError('error while deleting dns record')

def init_provider(provider_name):
    if CONFIG['providers'][provider_name]:
        providerType = CONFIG['providers'][provider_name]['type']
        nameservers = CONFIG['providers'][provider_name]['nameservers']
        config = CONFIG['providers'][provider_name]['config']

        if providerType == 'transip':
            return TransIpAcmeDnsClient(nameservers, config)
        if providerType == 'cloudflare':
            return CloudflareAcmeDnsClient(nameservers, config)
        if providerType == 'digital-ocean':
            return DigitalOceanDnsClient(nameservers, config)

        raise ValueError('provider types misconfigured :(')
    
    raise ValueError('provider not found :(')

PROVIDERS = {}
def get_profider(name):
    for d in CONFIG['domains']:
        if name == d or name.endswith('.' + d):
            provider_name = CONFIG['domains'][d]
            if not provider_name in PROVIDERS:
                # init provider
                print('Init and get provider %s for base domain %s' % (provider_name, d))
                p = init_provider(provider_name)
                PROVIDERS[provider_name] = p
            else:
                print('Get loaded provider %s for base domain %s' % (provider_name, d))
                p = PROVIDERS[provider_name]
            return (d, p)

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
            print('Queue adding challenge for %s' % name)
            provider.queue_add(domain, name, challenge)
        else:
            print('Queue removing challenge for %s' % name)
            provider.queue_delete(domain, name, challenge)

    print('Executing queues')
    for p in PROVIDERS:
        PROVIDERS[p].execute()

    if add:
        print('Sleeping for %d seconds to give a little bit of time for records to propagate' % CONFIG['sleep']['initial'])
        sleep(CONFIG['sleep']['initial'])
        for p in PROVIDERS:
            if not PROVIDERS[p].wait_for_add_propagated():
                # failed to add
                print('Failed to add all challenges. Exiting with error.')
                sys.exit(2)

