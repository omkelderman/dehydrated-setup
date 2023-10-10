import sys
import os
from DnsChallengeHandler import DnsChallengeHandler

DNS_CONFIG_FILENAME = 'dns-config.yml'
DNS_CONFIG_FILE_LOCATION = os.path.join(os.path.dirname(os.environ['CONFIG']), DNS_CONFIG_FILENAME)

if __name__ == '__main__':
    if len(sys.argv) < 2 or (sys.argv[1] != 'deploy_challenge' and sys.argv[1] != 'clean_challenge') or ((len(sys.argv)-2)%3)!=0 :
        print('%s <deploy_challenge|clean_challenge> [<domain> <ignored> <challenge>] [...]' % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    add = sys.argv[1] == 'deploy_challenge'
    challenges = [(sys.argv[i], sys.argv[i+2]) for i in range(2, len(sys.argv), 3)]

    handler = DnsChallengeHandler(DNS_CONFIG_FILE_LOCATION)
    if not handler.run(add, challenges):
        # exited with error
        sys.exit(2)
