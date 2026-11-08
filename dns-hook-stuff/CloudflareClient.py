from AcmeDnsClient import AcmeDnsClient, register_client_class
from cloudflare import Cloudflare

class CloudflareAcmeDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config, sleep_config):
        super().__init__(authoritative_name_servers, sleep_config)
        self.zone_ids = {}
        self.dns_records_for_zone_cache = {}
        self.add_queue = []
        self.remove_queue = []
        if 'email' in config:
            # use email + key auth
            self.cf = Cloudflare(api_email=config['email'], api_key=config['token'])
        else:
            # use api key auth
            self.cf = Cloudflare(api_token=config['token'])

    def get_zone_id(self, domain):
        if domain in self.zone_ids:
            return self.zone_ids[domain]
        else:
            zone_id = self.cf.zones.list(name=domain).result[0].id
            self.zone_ids[domain] = zone_id
            return zone_id

    def get_all_dns_records_for_zone(self, zone_id):
        if zone_id in self.dns_records_for_zone_cache:
            return self.dns_records_for_zone_cache[zone_id]
        else:
            records = self.cf.dns.records.list(zone_id=zone_id, type='TXT', name={'startswith': '_acme-challenge'})
            record_lookup = {(r.name, r.content): r.id for r in records}
            self.dns_records_for_zone_cache[zone_id] = record_lookup
            return record_lookup

    def _queue_add(self, domain, name, challenge):
        challenge=f'"{challenge}"'
        zone_id = self.get_zone_id(domain)
        if (name, challenge) not in self.get_all_dns_records_for_zone(zone_id):
            self.add_queue.append({'zone_id': zone_id, 'name':name, 'challenge':challenge})

    def _queue_delete(self, domain, name, challenge):
        challenge=f'"{challenge}"'
        zone_id = self.get_zone_id(domain)
        key = (name, challenge)
        record_lookup = self.get_all_dns_records_for_zone(zone_id)
        if key in record_lookup:
            self.remove_queue.append({'zone_id': zone_id, 'record_id': record_lookup[key]})

    def execute(self):
        for a in self.add_queue:
            self.cf.dns.records.create(zone_id=a['zone_id'], type='TXT', name=a['name'], content=a['challenge'], comment='ACME challenge', ttl=1)
        for d in self.remove_queue:
            self.cf.dns.records.delete(zone_id=d['zone_id'], dns_record_id=d['record_id'])
                

register_client_class('cloudflare', CloudflareAcmeDnsClient)