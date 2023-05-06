from scapy.all import *
import requests
from socket import gethostbyname


def printRouteData(ip):
    fake_HTTP_header = {
        'referer': 'https://ipinfo.io/',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36'
    }
    token = "a9806b0615d5d9"
    response = requests.get(f'https://ipinfo.io/{ip}?token={token}', headers=fake_HTTP_header)
    jsoned = response.json()
    if "bogon" not in jsoned:
        print(f'{jsoned["ip"]} -> tara: {jsoned["country"]}, regiune: {jsoned["region"]}, oras: {jsoned["city"]}')
    else:
        print(f"{jsoned['ip']} -> bogon")


def traceroute(ip,port):
    print(f"we search for {ip}")
    for ttl in range(1, 30):  # Maximum number of hops
        pkt = IP(dst=ip, ttl=ttl) / UDP(dport=port)  # Create the UDP packet
        reply = sr1(pkt, verbose=False, timeout=3)  # Send the packet and receive the response
        if reply is None:
            print("Host unreachable")
        else:
            printRouteData(reply.src)
            if reply.type == 3:
                print("Destination reached!!!")
                break


traceroute(gethostbyname("www.news.com.au"),33436)  # Perform traceroute for the Google DNS server