#!/bin/sh
set -e

# install dependencies
echo " => Install dependencies"
apt-get install dnsutils python3 python3-venv curl
echo " => All dependencies installed"

# init config
echo " => Setup /etc/dehydrated"
mkdir /etc/dehydrated
mkdir /etc/dehydrated/hooks
cp config.sample /etc/dehydrated/config
cp dns-config.yml.sample /etc/dehydrated/dns-config.yml
chmod 600 /etc/dehydrated/dns-config.yml # it might contain secret stuff, so lets protect it
touch /etc/dehydrated/domains.txt
echo " => /etc/dehydrated has been setup"

# setup python stuff in the dns hooks stuff dir
echo " => Setup python venv and install python requirements for hook scripts"
cd dns-hook-stuff
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cd ..
echo " => python venv and requirements have been setup"

# lets do a reminder cuz why not xd
echo "  ====================================================================================="
echo "  | Dont forget to edit the config in /etc/dehydrated/ !!!                            |"
echo "  |                                                                                   |"
echo "  | Set email in config if desired and run 'bin/dehydrated --register --accept-terms' |"
echo "  ====================================================================================="
