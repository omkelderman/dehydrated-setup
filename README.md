# Dehydrated setup for my server
This is some random shit I made to make my life easier when managing lets encrypt certs on my server using the dns-01 challenge type.

It contains some config for dehydrated to use, a ready to use hook script and a python script for calling the dns api of Cloudflare or TransIP depending on the domain.

This project is mainly used as a thing for mysef, but if anyone out there happens to stumble on this and wanted to use it, I'm not gonna stop you :wink:. Feel free to ask questions!

## Guide for myself on what to do on a new server, aka first-run/install:
* `sudo apt-get install dnsutils python3 python3-venv`
* clonse this repo (recursive!)
* run the setup.sh file
* specify letsencrypt notify email in `/etc/dehydrated/config`
* Fill in `/etc/dehydrated/dns-config.yml` according to the details at the end of this document
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

In the `dns-config.yml` config file are the following settings:

* `sleep`: the program will check the dns server to see if the added TXT-records are visible. These settings control how these checks work:
  * `initial`: initial delay in seconds before even attempting to look
  * `retry`: how much seconds to wait between each retry
  * `max-retries`: the max amount of retries before the program fails
* `providers`: the dns providers to use for the domains, each entry has a self picked name and then the following properties:
  * `type`: one of the following strings, which are the implemented apis
    - `transip`
    - `cloudflare`
    - `digital-ocean`
  * `nameserver`: the auhoritive nameserver used by this dns provider
  * `config`: extra opties different per type, usually used for authentication, see sample files for what is being used
* `domains`: a list of base domains being used and from which provider they are, use one of the self-named entries of the provider list above

Note that you can have multiple providers of the same type, for example cloudflare1 and cloudflare2 each with their own credentials in case one domain belongs to one account and another belongs to another. Just make sure to link the correct domain to the correct entry. The naming of the providers is completely arbitrary and doesnt matter. It is only being used to link the domains to their provider.