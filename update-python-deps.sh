#!/bin/sh
set -e

# setup python stuff in the dns hooks stuff dir
echo " => Install python requirements"
cd dns-hook-stuff
. .venv/bin/activate
pip install -r requirements.txt
echo " => python requirements installed"
