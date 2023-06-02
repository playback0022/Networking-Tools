import socket
import requests
from scapy.all import *


upstream_dns = '1.1.1.1'
rootServer = '198.41.0.4'


class DnsSolver:
    # gets the ip of nameservers from Glue Records
    @staticmethod
    def __getNextNameServer(dnsResponse: DNS) -> str:
        if dnsResponse.ar:
            additionalRecords = []

            # searching only for IPv4 capable nameservers (A records)
            for i in range(dnsResponse.arcount):
                # record type is 'A'
                if dnsResponse.ar[i].type == 1:
                    additionalRecords.append(dnsResponse.ar[i].rdata)

            # there were no IPv4 capable nameservers
            if not additionalRecords:
                return ''

            # any nameserver will do
            randomIndex = random.randint(0, len(additionalRecords) - 1)
            return additionalRecords[randomIndex]

        if dnsResponse.ns:
            nameServerRecords = []

            # searching only for NS records
            for i in range(dnsResponse.nscount):
                # record type is 'NS'
                if dnsResponse.ns[i].type == 2:
                    nameServerRecords.append(dnsResponse.ns[i].rdata)

            # there were no IPv4 capable nameservers
            if not nameServerRecords:
                return ''

            # any nameserver will do
            randomIndex = random.randint(0, len(nameServerRecords) - 1)
            return DnsSolver.recursivelyResolveDomain(nameServerRecords[randomIndex])

        return ''

    @staticmethod
    def recursivelyResolveDomain(domainName: str, nameServer: str = rootServer) -> str:
        dnsQuery = IP(dst=nameServer) / UDP(dport=53) / DNS(qr=0, rd=1, qd=DNSQR(qname=domainName, qtype='A', qclass='IN'))

        response = sr1(dnsQuery, verbose=0, timeout=6)

        if not response:
            return ''

        dnsResponse = response[DNS]

        # anything other than 'NOERROR' responses are dropped
        if dnsResponse.rcode != 0:
            return ''

        if dnsResponse.an:
            answerSection = dnsResponse.an[DNSRR]

            # an 'A' record was provided
            if answerSection.type == 1:
                return answerSection.rdata
            elif answerSection.type == 5:
                return DnsSolver.recursivelyResolveDomain(answerSection.rdata, rootServer)
            else:
                return ''

        nextNameServer = DnsSolver.__getNextNameServer(dnsResponse)
        print(f'querying for "{domainName}" at "{nameServer}", got "{nextNameServer}"')
        if not nextNameServer:
            return ''

        return DnsSolver.recursivelyResolveDomain(domainName, nextNameServer)





simple_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
# OS socket option to allow related, but not identical
# (addr, port) pairs to be assigned at the same time
simple_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
simple_udp.bind(('127.0.0.1', 53))


bannedDomains = []


# checks if the provided domain contains a banned domain and not
# the other way around, since any provided domain might be a FQDN
def isDomainBanned(domain):
    for bannedDomain in bannedDomains:
        if bannedDomain in domain:
            return True

    return False


# def loadBannedDomains():
#     response = requests.get('https://104.21.75.175/mirror/adservers.txt')
#
#     # split lines and ignore the first 10,
#     # since they contain README information
#     returnedBannedDomains = response.text.split(sep="\n")[10:-1]
#     for returnedBannedDomain in returnedBannedDomains:
#         bannedDomains.append(returnedBannedDomain.split(' ')[1])
#         # returnedBannedDomains[i] = returnedBannedDomains[i] + "."
#
#     bannedDomains.append('facebook.com')


def loadBannedDomains() -> None:
    with open('blocate.txt') as file:
        for line in file.readlines():
            bannedDomains.append(line)


# def readDataFile():
#     global bannedDomains
#     f = open("blocate.txt", "r")
#     for element in f.readlines():
#         bannedDomains.append(element)
#     f.close()
#     print(f"Domeniile au fost citite: {len(bannedDomains)} domenii")


# readDataFile()
loadBannedDomains()




try:
    while True:
        print("[*] listening...")
        request, newAddress = simple_udp.recvfrom(65535)
        # print(request, " ---- ", adresa_sursa)

        packet = DNS(request)
        dns = packet.getlayer(DNS)
        
        if not dns or dns.opcode != 0:
            bogusPacket = IP() / UDP() / DNS()
            simple_udp.sendto(bytes(bogusPacket), newAddress)
            continue

        domainName = packet[DNSQR].qname.decode()
        print(f'searching for: "{domainName}"')

        if isDomainBanned(domainName):
            resolvedIP = '0.0.0.0'
            print(f'blocked: "{domainName}"')
        else:
            resolvedIP = DnsSolver.recursivelyResolveDomain(domainName)
            print(f'got: "{resolvedIP}"')

            if not resolvedIP:
                response = DNS(
                    id=dns.id,  # maintain the request ID
                    qr=1,       # packet is a response
                    aa=0,       # not an authoritative server
                    tc=0,       # not a truncated response
                    rd=dns.rd,  # maintain recursion desired option
                    ra=0,       # recursion not available
                    rcode=3,    # domain could not be resolved
                    qd=dns.qd,
                )

                simple_udp.sendto(bytes(response), newAddress)
                continue

        response = DNS(
            id=dns.id,  # maintain the request ID
            qr=1,       # packet is a response
            aa=0,       # not an authoritative server
            tc=0,       # not a truncated response
            rd=dns.rd,  # maintain recursion desired option
            ra=0,       # recursion not available
            rcode=0,    # response is successful
            qd=dns.qd,  # maintain question list
            an=DNSRR(
                rrname=domainName,
                type='A',
                rclass='IN',
                rdata=resolvedIP,
                ttl=300
            )
        )

        simple_udp.sendto(bytes(response), newAddress)
except KeyboardInterrupt:
    simple_udp.close()
