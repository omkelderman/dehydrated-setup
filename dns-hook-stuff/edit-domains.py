import yaml

DNS_CONFIG_FILE_LOCATION = '/etc/dehydrated/dns-config.yml'
DOMAINS_FILE_LOCATION = '/etc/dehydrated/domains.txt'

def load_yaml_file(file_path):
    with open(file_path, 'r') as stream:
        return yaml.safe_load(stream)

def load_txt_file(file_path):
    with open(file_path, 'r') as stream:
        return stream.read()

class Cert:
    def __init__(self, line):
        if '>' in line:
            index = line.index('>')
            self.name = line[index+1:].strip()
            line = line[:index].strip()
        else:
            self.name = None

        self.domains = line.split()

    def has_name(self):
        return self.name != None

    def to_line(self):
        string = ' '.join(self.domains)
        if self.has_name():
            string += ' > ' + self.name
        return string

    def __str__(self):
        return self.to_line()

config = load_yaml_file(DNS_CONFIG_FILE_LOCATION)
certs = []
for line in load_txt_file(DOMAINS_FILE_LOCATION).split('\n'):
    line = line.strip()
    if(line == ''):
        continue
    
    certs.append(Cert(line))


certs.append(Cert('kaas ham > le'))

def print_current_certs():
    if(len(certs) == 0):
        print('No certificates or domains have been configured yet')
    else:
        print('Current certificates:')
        for i, cert in enumerate(certs):
            print('[%d] %s' % (i, cert))

def print_domains_for_cert(cert):
    if len(cert.domains) == 0:
        raise ValueError('Cannot have cert with zero domains')

    if cert.has_name():
        print('Named cert: %s' % cert.name)
        rest_of_domains = cert.domains
    else:
        print('Unnamed cert (first domain listed will act as name, and thus is not changeable):')
        print('[-] *%s*' % cert.domains[0])
        rest_of_domains = cert.domains[1:]

    for i, domain in enumerate(rest_of_domains):
        print('[%d] %s' % (i, domain))

    

def edit_domains_on_cert(cert):

    pass


print_domains_for_cert(certs[0])