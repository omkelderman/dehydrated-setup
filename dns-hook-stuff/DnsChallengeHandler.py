import yaml
from time import sleep

# import all the implementations, gotta list them one by one,
# havent figure out a way to do that automatically
from AcmeDnsClient import get_client_class
import TransIPClient
import CloudflareClient
import DigitalOceanClient
import OvhClient

def load_yaml_file(file_path):
    with open(file_path, 'r') as stream:
        return yaml.safe_load(stream)

class DnsChallengeHandler:
    def __init__(self, config_file):
        self.config = load_yaml_file(config_file)
        self.providers = {}

    def init_provider(self, provider_name):
        if provider_name in self.config['providers']:
            providerType = self.config['providers'][provider_name]['type']
            nameservers = self.config['providers'][provider_name]['nameservers']
            config = self.config['providers'][provider_name]['config']
            typeClass = get_client_class(providerType)
            return typeClass(nameservers, config, self.config['sleep'])
    
        raise ValueError('provider not found :(')


    def get_provider(self, name):
        for d in self.config['domains']:
            if name == d or name.endswith('.' + d):
                provider_name = self.config['domains'][d]
                if not provider_name in self.providers:
                    # init provider
                    print('Init and get provider %s for base domain %s' % (provider_name, d))
                    p = self.init_provider(provider_name)
                    self.providers[provider_name] = p
                else:
                    print('Get loaded provider %s for base domain %s' % (provider_name, d))
                    p = self.providers[provider_name]
                return (d, p)
        raise ValueError('domain not found :(')


    def run(self, is_add, challenges):
        for (name, challenge) in challenges:
            domain, provider = self.get_provider(name)
            if is_add:
                print('Queue adding challenge for %s' % name)
                provider.queue_add(domain, name, challenge)
            else:
                print('Queue removing challenge for %s' % name)
                provider.queue_delete(domain, name, challenge)

        print('Executing queues')
        for p in self.providers:
            self.providers[p].execute()
        
        if is_add:
            initial_sleep = self.config['sleep']['initial']
            print('Sleeping for %d seconds to give a little bit of time for records to propagate' % initial_sleep)
            sleep(initial_sleep)
            for p in self.providers:
                if not self.providers[p].wait_for_add_propagated():
                    # failed to add
                    print('Failed to add all challenges. Exiting with error.')
                    return False
        
        return True
