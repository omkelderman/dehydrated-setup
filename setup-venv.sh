#!/bin/sh
set -e

# setup python stuff in the dns hooks stuff dir
echo " => Setup python venv"
cd dns-hook-stuff
rm -rf .venv # delete venv if exists
python3 -m venv .venv
cd ..
echo " => python venv has been setup"

# run the update python deps script to install dependencies
./update-python-deps.sh

