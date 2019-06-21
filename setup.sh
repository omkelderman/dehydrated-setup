#!/bin/sh
set -e

# install dependencies
apt-get install dnsutils python3 python3-venv curl

# init config
mkdir /etc/dehydrated
mkdir /etc/dehydrated/hooks
cp config.sample /etc/dehydrated/config
cp dns-config.yml.sample /etc/dehydrated/dns-config.yml
touch /etc/dehydrated/domains.txt

# setup python stuff in the dns hooks stuff dir
cd dns-hook-stuff
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cd ..

# lets do a reminder cuz why not xd
echo
echo "Dont forget to edit the config in /etc/dehydrated/ !!!"
echo
echo "Set email in config if desired and run 'bin/dehydrated --register --accept-terms'"
echo
