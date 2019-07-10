from AcmeDnsClient import AcmeDnsClient, register_client_class
from transip.service.domain import DomainService
from transip.service.objects import DnsEntry

class TransIpAcmeDnsClient(AcmeDnsClient):
    def __init__(self, authoritative_name_servers, config, sleep_config):
        super().__init__(authoritative_name_servers, sleep_config)
        self.tid = DomainService(login=config['username'], private_key_file=config['key-file'])
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

register_client_class('transip', TransIpAcmeDnsClient)