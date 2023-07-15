## General Description
As a part of the same repository, two unrelated networking tools and two related networking exploits were implemented as an assignment for the Networking course of the University of Bucharest. All of these implementations rely heavily on `scapy`, the packet manipulation library.

## Networking Tools
### Traceroute
Similar to the majority of `traceroute` utilities, this UDP implementation also specifies details such as the country, the region and the city of each host, using the `ipinfo.io` API.

### Ad blocking DNS resolver
Being not only capable of resolving basic queries involving A, NS, CNAME and glue records, this DNS server employs features such as caching, logging and hostname blocking based on given text files.

Any curated list of ad and tracking related domain names can be used, but the provided `banned.txt` file contains [the following ones](https://github.com/anudeepND/blacklist). Whenever a request for such a domain name is received, `0.0.0.0` is returned as the response.

The python script can be run as-is, or as a part of a docker container. Both a Dockerfile and a docker-compose file can be found in the corresponding directory. 

A python script was also provided to analyse the logs produced by the resolver as bar plots: 
- based on the banning logs, some of the most notorious tech giants are included into separate bars
- based on the caching logs, two bars corresponding to the hits and misses are plotted

## Networking Exploits

The container architecture of the images from the `exploit-docker-network` directory is described below from a networking perspective.

```
            MIDDLE------------\
        subnet2: x.x.x.3       \
        MAC: xx:xx:xx:xx:xx:03  \
               forwarding        \ 
              /                   \
             /                     \
Poison ARP x.x.x.1 is-at          Poison ARP x.x.x.2 is-at
           xx:xx:xx:xx:xx:03         |       xx:xx:xx:xx:xx:03
           /                         |
          /                          |
         /                           |
        /                            |
    SERVER <---------------------> ROUTER <---------------------> CLIENT
subnet2: x.x.x.2                     |                          subnet1: y.y.y.2
MAC: xx:xx:xx:xx:xx:02               |                          MAC: yy:yy:yy:yy:yy:02
                           subnet1:  y.y.y.1
                           MAC eth0: yy:yy:yy:yy:yy:01
                           subnet2:  x.x.x.1
                           MAC eth1: xx:xx:xx:xx:xx:01
                           subnet2 <------> subnet1
                                  forwarding
```

### ARP Spoofing
This is just a textbook implementation of the famous exploit. The only notable caveat is that this script was written specifically for Linux hosts and for it to work, both targets must have an entry of the other one in their ARP table. As a nice addition, two separate threads are created to poison the table of each host, using the `threading` library.

### TCP Hijacking
Using the ARP spoofing technique described earlier, this exploit implementation intercepts all the network packets sent between the `server` and the `router`, modifies the TCP segments by changing the first byte of the payload with a '?' character and forwards all the other traffic.
The queuing functionality is implemented using `netfilterqueue`. 

## Dependencies
All development took place and made use of Linux hosts. Only using the specified dependencies in the `requirements.txt` with python 3.11 is guaranteed to work.
