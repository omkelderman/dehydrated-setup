#!/bin/sh

SCRIPT=$(readlink -f "$0")
SCRIPTDIR=$(dirname "$SCRIPT")

cd $SCRIPTDIR/../dns-hook-stuff
. venv/bin/activate

python edit-domains.py