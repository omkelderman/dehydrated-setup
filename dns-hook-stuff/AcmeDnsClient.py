from abc import ABC, abstractmethod
from time import sleep
import subprocess

CLIENTS = {}
def register_client_class(name, client):
    CLIENTS[name] = client

def get_client_class(name):
    if name in CLIENTS:
        return CLIENTS[name]
    else:
        raise ValueError('provider types misconfigured :(')

class AcmeDnsClient(ABC):
    def __init__(self, authoritative_name_servers, sleep_config):
        self.authoritative_name_servers = authoritative_name_servers
        self.retry_seconds = sleep_config['retry']
        self.max_retries = sleep_config['max-retries']
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
        for entry in self.names_added:
            count = 0
            while True:
                domain, challenge = entry
                exists = self.check_domain_has_propagated(domain, challenge)
                if exists:
                    # yay, we found it, lets continue to next one and break out of the check look
                    print('TXT record "%s" for %s has been seen on all configured nameservers!' % (challenge, domain))
                    break
                else:
                    if count >= self.max_retries:
                        print('TXT record "%s" for %s is not seen on all configured nameservers yet, max retries has been reached. Adding failed!' % (challenge, domain))
                        return False

                    print('TXT record "%s" for %s is not seen on all configured nameservers yet, waiting %d sec and trying again...' % (challenge, domain, self.retry_seconds))
                    sleep(self.retry_seconds)
                    count += 1

        return True

    def check_domain_has_propagated(self, domain, challenge):
        for auth_name_server in self.authoritative_name_servers:
            dns_result = subprocess.check_output(['dig', '+short', 'TXT', domain, '@'+auth_name_server], universal_newlines=True)
            if not ('"%s"' % challenge) in dns_result.split('\n'):
                return False
        return True
