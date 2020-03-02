from AcmeDnsClient import AcmeDnsClient, register_client_class
import ovh

class OvhAcmeDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config, sleep_config):
        super().__init__(authoritative_name_servers, sleep_config)
        self.ovh_client = ovh.Client(**config)
        self.add_queue = []    # {zonename: xxx, subdomain: subdomain or empty string, data: challenge}
        self.remove_queue = [] # {zonename: xxx, record_id: 123}

    def get_subdomain_part(self, domain, fulldomain):
        if domain == fulldomain:
            # its the base domain self, so no subdomain
            return ''
        
        dotDomain = '.' + domain
        if fulldomain.endswith(dotDomain):
            # detected valid subdomain
            return fulldomain[:-len(dotDomain)]
        
        # no subdomain detected
        raise ValueError('fulldomain not a subdomain of domain')

    def _queue_add(self, domain, name, challenge):
        subdomain = self.get_subdomain_part(domain, name)
        self.add_queue.append({'zonename': domain, 'subdomain': subdomain, 'data': challenge})
    
    def _queue_delete(self, domain, name, challenge):
        subdomain = self.get_subdomain_part(domain, name)
        txt_records = self.ovh_client.get('/domain/zone/%s/record' % domain, fieldType='TXT', subDomain=subdomain)
        for record_id in txt_records:
            record = self.ovh_client.get('/domain/zone/%s/record/%s' % (domain, record_id))
            # only have to check target, everything else is already defined by the way we're getting the records
            if record['target'] == ('"%s"' % challenge):
                self.remove_queue.append({'zonename': domain, 'record_id': record_id})

    def execute(self):
        for a in self.add_queue:
            self.add_txt_dns_record(a['zonename'], a['subdomain'], a['data'])
        for d in self.remove_queue:
            self.remove_dns_record(d['zonename'], d['record_id'])
    
    def add_txt_dns_record(self, zonename, subdomain, data):
        self.ovh_client.post('/domain/zone/%s/record' % zonename,
            fieldType='TXT',
            subDomain=subdomain,
            target=('"%s"' % data),
            ttl=None
        )
    
    def remove_dns_record(self, zonename, record_id):
        self.ovh_client.delete('/domain/zone/%s/record/%s' % (zonename, record_id))

register_client_class('ovh', OvhAcmeDnsClient)