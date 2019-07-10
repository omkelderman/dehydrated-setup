from AcmeDnsClient import AcmeDnsClient, register_client_class
import CloudFlare

class CloudflareAcmeDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config, sleep_config):
        super().__init__(authoritative_name_servers, sleep_config)
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

register_client_class('cloudflare', CloudflareAcmeDnsClient)