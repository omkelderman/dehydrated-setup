#!/usr/bin/env bash
set -e

HANDLER="$1"; shift
if [[ "${HANDLER}" =~ ^(deploy_cert|deploy_ocsp|unchanged_cert|invalid_challenge|request_failure|generate_csr|startup_hook|exit_hook)$ ]]; then
  HOOK_FILE="/etc/dehydrated/hooks/$HANDLER"
  [ -x $HOOK_FILE ] && $HOOK_FILE "$@" || true
elif [[ "${HANDLER}" =~ ^(deploy_challenge|clean_challenge)$ ]]; then
  # go to the dir with all the fancy stuff and load venv
  cd "$BASEDIR/../dns-hook-stuff"
  . venv/bin/activate

  # execute it owowowowo
  python run.py "$HANDLER" "$@"
fi
