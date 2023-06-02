import socket
import requests
from scapy.all import *


localhostAddress = '127.0.0.1'
rootServer = '198.41.0.4'
bannedDomainFile = 'blocate.txt'


class DnsSolver:
    # returns the ip of a nameserver, either from Glue or NS Records
    @staticmethod
    def __getNextNameServer(dnsResponse: DNS) -> str:
        # when additional records are present, they most likely contain a Glue Record
        if dnsResponse.ar:
            additionalRecords = []

            # searching only for IPv4 capable nameservers (A records);
            # using indexing, since records are nested, not sequential in scapy!
            for i in range(dnsResponse.arcount):
                # record type is 'A'
                if dnsResponse.ar[i].type == 1:
                    additionalRecords.append(dnsResponse.ar[i].rdata)

            # there were no IPv4 capable nameservers
            if not additionalRecords:
                return ''

            # any nameserver will do just fine
            randomIndex = random.randint(0, len(additionalRecords) - 1)
            return additionalRecords[randomIndex]

        # in the absence of Glue Records, the current nameserver
        # returns NS records in the authoritative field
        if dnsResponse.ns:
            nameServerRecords = []

            # searching only for NS records
            for i in range(dnsResponse.nscount):
                # record type is 'NS'
                if dnsResponse.ns[i].type == 2:
                    nameServerRecords.append(dnsResponse.ns[i].rdata)

            # there were no NS records
            if not nameServerRecords:
                return ''

            # any NS record will do just fine
            randomIndex = random.randint(0, len(nameServerRecords) - 1)
            # an independent recursive lookup is issued, in order
            # to resolve the selected nameserver's IP address
            return DnsSolver.recursivelyResolveDomain(nameServerRecords[randomIndex].decode())

        # malformed DNS response packet
        return ''

    # main recursive function used in DNS look-ups
    @staticmethod
    def recursivelyResolveDomain(domainName: str, nameServer: str = rootServer) -> str:
        # construct a regular DNS query packet, with the recursion-desired field set
        dnsQuery = IP(dst=nameServer) / UDP(dport=53) / DNS(qr=0, rd=1, qd=DNSQR(qname=domainName, qtype='A', qclass='IN'))

        # sending the packet with a timeout of 6s, so as not
        # to block the whole process when a request fails
        response = sr1(dnsQuery, verbose=0, timeout=6)

        # request timed out
        if not response:
            return ''

        dnsResponse = response[DNS]

        # anything other than 'NOERROR' responses are dropped
        if dnsResponse.rcode != 0:
            return ''

        # the nameserver which was queried is the authoritative DNS server
        if dnsResponse.an:
            # the first entry in the answer field of the DNS response;
            # all the other entries (if present) are nested within it,
            # but the accessed properties only return the contents of
            # the top-level DNSRR object (the first entry)
            answerSection = dnsResponse.an[DNSRR]

            # an A record was provided
            if answerSection.type == 1:
                return answerSection.rdata
            # a CNAME record was provided
            elif answerSection.type == 5:
                # in this case, the desired domain name points to another domain name, which must be resolved via another lookup
                return DnsSolver.recursivelyResolveDomain(answerSection.rdata.decode())
            # this DNS resolver only handles A and CNAME records
            else:
                return ''

        nextNameServer = DnsSolver.__getNextNameServer(dnsResponse)
        print(f'querying for "{domainName}" at "{nameServer}", got "{nextNameServer}"')

        # for any reason, the next nameserver could not be resolved
        if not nextNameServer:
            return ''

        # querying the next nameserver in the hierarchy
        return DnsSolver.recursivelyResolveDomain(domainName, nextNameServer)



mainSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
# OS socket option to allow related, but not identical
# (addr, port) pairs to be assigned at the same time
mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
mainSocket.bind((localhostAddress, 53))


bannedDomains = []


def loadBannedDomains() -> None:
    with open(bannedDomainFile) as file:
        for line in file.readlines():
            bannedDomains.append(line)


# checks if the provided domain contains a banned domain and not
# the other way around, since any provided domain might be a FQDN
def isDomainBanned(domain: str) -> bool:
    for bannedDomain in bannedDomains:
        if bannedDomain in domain:
            return True

    return False


loadBannedDomains()


try:
    while True:
        print("[*] listening...")
        # maximum UDP-based DNS packet size is 512B
        request, clientAddress = mainSocket.recvfrom(512)
        dnsQuery = DNS(request).getlayer(DNS)

        # not a DNS packet or the client requires functionality
        # for which this DNS resolver is not designed
        if not dnsQuery or dnsQuery.opcode != 0:
            bogusPacket = IP() / UDP() / DNS()
            mainSocket.sendto(bytes(bogusPacket), clientAddress)
            continue

        domainName = dnsQuery[DNSQR].qname.decode()
        print(f'searching for: "{domainName}"')

        if isDomainBanned(domainName):
            resolvedIP = '0.0.0.0'
            print(f'blocked: "{domainName}"')
        else:
            resolvedIP = DnsSolver.recursivelyResolveDomain(domainName)
            print(f'got: "{resolvedIP}"')

            # domain name could not be resolved
            if not resolvedIP:
                response = DNS(
                    id=dnsQuery.id,  # maintain the request ID
                    qr=1,            # packet is a response
                    aa=0,            # not an authoritative server
                    tc=0,            # not a truncated response
                    rd=dnsQuery.rd,  # maintain recursion desired option
                    ra=0,            # recursion not available
                    rcode=3,         # domain could not be resolved
                    qd=dnsQuery.qd,
                )

                mainSocket.sendto(bytes(response), clientAddress)
                continue

        response = DNS(
            id=dnsQuery.id,  # maintain the request ID
            qr=1,            # packet is a response
            aa=0,            # not an authoritative server
            tc=0,            # not a truncated response
            rd=dnsQuery.rd,  # maintain recursion desired option
            ra=0,            # recursion not available
            rcode=0,         # response is successful
            qd=dnsQuery.qd,  # maintain question list
            an=DNSRR(
                rrname=domainName,
                type='A',
                rclass='IN',
                rdata=resolvedIP,
                ttl=300
            )
        )

        mainSocket.sendto(bytes(response), clientAddress)
except KeyboardInterrupt:
    mainSocket.close()
