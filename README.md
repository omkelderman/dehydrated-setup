# Dehydrated setup for my server
This is some random shit I made to make my life easier when managing lets encrypt certs on my server using the dns-01 challenge type.

It contains some config for dehydrated to use, a ready to use hook script and a python script for calling the dns api of Cloudflare or TransIP depending on the domain.

This project is mainly used as a thing for mysef, but if anyone out there happens to stumble on this and wanted to use it, I'm not gonna stop you :wink:. Feel free to ask questions!

## Guide for myself on what to do on a new server:
* clonse this repo (recursive!)
* run the setup.sh file
* specify letsencrypt notify email in `/etc/dehydrated/config`
* specify the api key things in `/etc/dehydrated/dns-config.yml`
* in the same file specify all the domains I own (and wanna use on that server) and if they use TransIP or Cloudflare
* fill in `/etc/dehydrated/domains.txt`
* Add the following to `/etc/cron.daily/dehydrated`:
  ```
  #!/bin/sh
  
  /path/to/cloned/repo/bin/dehydrated -c
  ```
* run `/path/to/cloned/repo/bin/dehydrated --register --accept-terms`
* run `/path/to/cloned/repo/bin/dehydrated -c`
* If needed place executable files in `/etc/dehydrated/hooks` with one of the dehydrated hook handler names to hook up other things (e.g. a nginx reload)

If everything went well, server should now be configured and done

## changing domains on the server
* edit `/etc/dehydrated/domains.txt` accordingly
* if needed edit `/etc/dehydrated/dns-config.yml` as well
