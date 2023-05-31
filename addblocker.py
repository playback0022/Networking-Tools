import socket
from scapy.all import *

simple_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
simple_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
simple_udp.bind(('127.0.0.1', 53))

def check_blocked(name):
    return name in banlist

import requests

banlist = [] 
def getDataFile():
	response = requests.get('https://hosts.anudeep.me/mirror/adservers.txt')
	banlist = response.text.split(sep="\n")[10:]
	for i in range(len(banlist) - 1):
	    banlist[i] = banlist[i].split(sep=" ")[1]
	    banlist[i] = banlist[i] + "."
	banlist.insert(0, "www.facebook.com.")
	print(banlist[:10])
	f = open("blocate.txt","w")
	for element in banlist:
		f.write(element + "\n")
	f.close()
	
def readDataFile():
	global banlist
	f = open("blocate.txt","r")
	for element in f.readlines():
		banlist.append(element)
	f.close()
	print(f"Domeniile au fost citite: {len(banlist)} domenii")


readDataFile()

# Define upstream DNS resolver
upstream_dns = ''  # Example: Google DNS
upstream_dns_port = 53  # DNS port


while True:
    print("?")
    request, adresa_sursa = simple_udp.recvfrom(65535)
    print(request, " ---- ", adresa_sursa)
    packet = DNS(request)
    dns = packet.getlayer(DNS)

    if dns is not None and dns.opcode == 0:  # dns QUERY
        blocked = False

        qname = packet[DNSQR].qname.decode()
        print(f"domain: {qname}") 
        if check_blocked(qname):
            blocked = True
            ip_ret = '0.0.0.0'
        else:
            ip_ret = socket.gethostbyname(qname)

        dns_answer = DNSRR(
            rrname=dns.qd.qname,
            ttl=330,
            type="A",
            rclass="IN",
            rdata=ip_ret)
        dns_response = DNS(
            id=packet[DNS].id,
            qr=1,
            aa=0,
            rcode=0,
            qd=packet.qd,
            an=dns_answer)

        if blocked:
            print("Blocked: ", qname)
        else:
            print("Got: ", qname, ip_ret)

        simple_udp.sendto(bytes(dns_response), adresa_sursa)

simple_udp.close()