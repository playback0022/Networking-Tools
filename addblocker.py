import socket
import requests
import datetime
from scapy.all import *


localhostAddress = '127.0.0.1'
rootServer = '198.41.0.4'
bannedDomainFile = 'blocked.txt'
defaultTTL = 3600    # one hour


class DnsSolver:
    def __init__(self, defaultTTL: int):
        # default TTL time period saved as a timedelta object
        self.__defaultTTL = timedelta(defaultTTL)
        # structure:
        #   - key: domain name
        #   - value: tuple
        #       - IP address
        #       - expiration date (datetime object)
        self.__cache = {}

    def _getFromCache(self, domainName: str) -> str:
        # searching the cache and verifying entry hasn't expired
        if domainName in self.__cache and datetime.now() < self.__cache[domainName][1]:
            return self.__cache[domainName][0]

        return ''   # entry expired or domain was not yet cached

    def _putInCache(self, domainName: str, ipAddress: str) -> None:
        self.__cache[domainName] = tuple([ipAddress, datetime.now() + self.__defaultTTL])

    # returns the ip of a nameserver, either from Glue or NS Records
    def __getNextNameServer(self, dnsResponse: DNS) -> str:
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
            chosenNameServer = nameServerRecords[randomIndex].decode()

            # an independent recursive lookup is issued, in order
            # to resolve the selected nameserver's IP address;
            return self.recursivelyResolveDomain(chosenNameServer)

        # malformed DNS response packet
        return ''

    # main recursive function used in DNS look-ups; returns the desired IP
    def recursivelyResolveDomain(self, domainName: str, nameServer: str = rootServer) -> str:
        # construct a regular DNS query packet, with the recursion-desired field set
        dnsQuery = IP(dst=nameServer) / UDP(dport=53) / DNS(qr=0, rd=1, qd=DNSQR(qname=domainName, qtype='A', qclass='IN'))

        # sending the packet with a timeout of 5s, so as not
        # to block the whole process when a request fails
        response = sr1(dnsQuery, verbose=0, timeout=5)

        # request timed out
        if not response:
            return ''

        dnsResponse = response[DNS]

        # anything other than 'NOERROR' responses are dropped
        if dnsResponse.rcode != 0:
            return ''

        # the nameserver which was queried is the authoritative DNS server
        if dnsResponse.an:
            aRecords = []
            cnameRecords = []

            for i in range(dnsResponse.ancount):
                # an A record was provided
                if dnsResponse.an[i].type == 1:
                    aRecords.append(dnsResponse.an[i].rdata)
                # a CNAME record was provided
                elif dnsResponse.an[i].type == 5:
                    cnameRecords.append(dnsResponse.an[i].rdata)

            if aRecords:
                randomIndex = random.randint(0, len(aRecords) - 1)
                return aRecords[randomIndex]

            if cnameRecords:
                randomIndex = random.randint(0, len(cnameRecords) - 1)
                # in this case, the desired domain name points to another domain name, which must be resolved via another lookup
                return self.recursivelyResolveDomain(cnameRecords[randomIndex].decode())

            # this DNS resolver only handles A and CNAME records
            # and none were provided by the authoritative server
            return ''

        nextNameServer = self.__getNextNameServer(dnsResponse)
        print(f'querying for "{domainName}" at "{nameServer}", got "{nextNameServer}"')

        # for any reason, the next nameserver could not be resolved
        if not nextNameServer:
            return ''

        # querying the next nameserver in the hierarchy
        return self.recursivelyResolveDomain(domainName, nextNameServer)



class Main:
    def __init__(self, localHostAddress: str, rootServer: str, bannedDomainNameFile: str, defaultTTL: int):
        self.__mainSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        # OS socket option to allow related, but not identical
        # (addr, port) pairs to be assigned at the same time
        self.__mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__mainSocket.bind((localhostAddress, 53))

        self.__solver = DnsSolver(defaultTTL)
        self.__defaultTTL = defaultTTL
        self.__localHostAddress = localHostAddress
        self.__rootServer = rootServer
        self.__bannedDomainNameFile = bannedDomainNameFile
        self.__bannedDomains = []

    def __loadBannedDomains(self) -> None:
        with open(self.__bannedDomainNameFile) as file:
            for line in file.readlines():
                self.__bannedDomains.append(line.strip())

    # checks if the provided domain contains a banned domain and not
    # the other way around, since any provided domain might be a FQDN
    def __isDomainBanned(self, domain: str) -> bool:
        for bannedDomain in self.__bannedDomains:
            if bannedDomain in domain:
                return True

        return False

    def start(self) -> None:
        self.__loadBannedDomains()

        try:
            while True:
                print("[*] listening...")
                # maximum UDP-based DNS packet size is 512B
                request, clientAddress = self.__mainSocket.recvfrom(512)
                dnsQuery = DNS(request).getlayer(DNS)

                # not a DNS packet or the client requires functionality
                # for which this DNS resolver is not designed
                if not dnsQuery or dnsQuery.opcode != 0:
                    bogusPacket = IP() / UDP() / DNS()
                    self.__mainSocket.sendto(bytes(bogusPacket), clientAddress)
                    continue

                domainName = dnsQuery[DNSQR].qname.decode()
                print(f'searching for: "{domainName}"')

                dnsResponse = DNS(
                    id=dnsQuery.id,  # maintain the request ID
                    qr=1,  # packet is a response
                    aa=0,  # not an authoritative server
                    tc=0,  # not a truncated response
                    rd=dnsQuery.rd,  # maintain recursion desired option
                    ra=0,  # recursion not available
                    qd=dnsQuery.qd  # maintain question list
                )

                if self.__isDomainBanned(domainName):
                    resolvedIP = '0.0.0.0'
                    print(f'blocked: "{domainName}"')
                else:
                    resolvedIP = self.__solver._getFromCache(domainName)
                    if resolvedIP:
                        print(f'got: "{resolvedIP}"')
                    
                    # domain name cache expired or doesn't exist
                    if not resolvedIP:
                        resolvedIP = self.__solver.recursivelyResolveDomain(domainName)
                        print(f'got: "{resolvedIP}"')
    
                        # domain name could not be resolved
                        if not resolvedIP:
                            dnsResponse.rcode = 3      # domain could not be resolved
                            self.__mainSocket.sendto(bytes(dnsResponse), clientAddress)
                            continue

                        self.__solver._putInCache(domainName, resolvedIP)

                dnsResponse.rcode = 0      # response is successful
                dnsResponse.an = DNSRR(
                        rrname=domainName,
                        type='A',
                        rclass='IN',
                        rdata=resolvedIP,
                        ttl=defaultTTL
                    )

                self.__mainSocket.sendto(bytes(dnsResponse), clientAddress)
        except:
            self.__mainSocket.close()


server = Main(localhostAddress, rootServer, bannedDomainFile, defaultTTL)
server.start()
