#!/bin/sh
set -e

DEFAULT_CONFIG_DIR=/etc/dehydrated

CONFIG_DIR=${1:-$DEFAULT_CONFIG_DIR}
CONFIG_DIR=${CONFIG_DIR%/}
CONFIG_DIR=$(realpath "$CONFIG_DIR")

# install dependencies
echo " => Install dependencies"
sudo apt-get install dnsutils python3 python3-venv curl
echo " => All dependencies installed"

# init config
echo " => Setup $CONFIG_DIR"
mkdir "$CONFIG_DIR"
mkdir "$CONFIG_DIR/hooks"
sed -e "s#{{CONFIG_DIR}}#$CONFIG_DIR#g" config.sample > "$CONFIG_DIR/config"
cp dns-config.yml.sample "$CONFIG_DIR/dns-config.yml"
chmod 600 "$CONFIG_DIR/dns-config.yml" # it might contain secret stuff, so lets protect it
touch "$CONFIG_DIR/domains.txt"
echo " => $CONFIG_DIR has been setup"

# setup python stuff in the dns hooks stuff dir
echo " => Setup python venv"
cd dns-hook-stuff
python3 -m venv .venv
cd ..
echo " => python venv has been setup"

# run the update python deps script to install dependencies
./update-python-deps.sh

# lets do a reminder cuz why not xd
echo "  ====================================================================================="
echo "    Dont forget to edit the config in $CONFIG_DIR/ !!!"
echo
echo "    Set email in config if desired and run 'bin/dehydrated --register --accept-terms'"
echo "  ====================================================================================="
