from AcmeDnsClient import AcmeDnsClient, register_client_class
import requests

class DigitalOceanAcmeDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config, sleep_config):
        super().__init__(authoritative_name_servers, sleep_config)
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

register_client_class('digital-ocean', DigitalOceanAcmeDnsClient)