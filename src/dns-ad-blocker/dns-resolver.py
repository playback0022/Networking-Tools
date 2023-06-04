import signal
import datetime
import argparse
import json
from scapy.all import *


class DnsSolver:
    def __init__(self, defaultTTL: int, rootServer: str, verbose: bool):
        # default TTL time period saved as a timedelta object
        self.__defaultTTL = timedelta(defaultTTL)
        self.__rootServer = rootServer
        self.__verbose = verbose
        # structure:
        #   - key: domain name
        #   - value: tuple
        #       - IP address
        #       - expiration date (datetime object)
        self.__cache = {}

    def getFromCache(self, domainName: str) -> str:
        # searching the cache and verifying entry hasn't expired
        if domainName in self.__cache and datetime.now() < self.__cache[domainName][1]:
            return self.__cache[domainName][0]

        return ''   # entry expired or domain was not yet cached

    def putInCache(self, domainName: str, ipAddress: str) -> None:
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
    def recursivelyResolveDomain(self, domainName: str, nameServer: str = '') -> str:
        # default parameter when a name server is not specified
        if not nameServer:
            nameServer = self.__rootServer

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
        if self.__verbose:
            print(f'querying "{nameServer}" for "{domainName}", got "{nextNameServer}"')

        # for any reason, the next nameserver could not be resolved
        if not nextNameServer:
            return ''

        # querying the next nameserver in the hierarchy
        return self.recursivelyResolveDomain(domainName, nextNameServer)



class Main:
    def __init__(self, localHostAddress: str, rootServer: str, bannedDomainNamesFile: str, defaultTTL: int, verbose: bool, banningLogFile: str, cachingLogFile: str):
        self.__mainSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        # OS socket option to allow related, but not identical
        # (addr, port) pairs to be assigned at the same time
        self.__mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__mainSocket.bind((localHostAddress, 53))

        self.__solver = DnsSolver(defaultTTL, rootServer, verbose)
        self.__bannedDomainNamesFile = bannedDomainNamesFile
        self.__bannedDomains = []
        self.__defaultTTL = defaultTTL
        self.__verbose = verbose
        self.__banningLogFile = banningLogFile
        self.__banningLogs = {}
        self.__cachingLogFile = cachingLogFile
        self.__cachingLogs = {}

        # declaring that the __stop() method will be called whenever SIGINT
        # or SIGTERM is sent to the process in which the current script runs
        signal.signal(signal.SIGINT, self.__stop)
        signal.signal(signal.SIGTERM, self.__stop)

    def __loadBannedDomains(self) -> None:
        with open(self.__bannedDomainNamesFile) as file:
            for line in file.readlines():
                self.__bannedDomains.append(line.strip())

    # checks if the provided domain contains a banned domain and not
    # the other way around, since any provided domain might be a FQDN
    def __isDomainBanned(self, domain: str) -> bool:
        for bannedDomain in self.__bannedDomains:
            if bannedDomain in domain:
                return True

        return False

    def __loadBanningLogs(self) -> None:
        if self.__banningLogFile:
            with open(self.__banningLogFile, 'r') as f:
                content = f.read()

                if content:
                    self.__banningLogs = json.loads(content)

    def __loadCachingLogs(self) -> None:
        if self.__cachingLogFile:
            with open(self.__cachingLogFile, 'r') as f:
                content = f.read()

                if content:
                    self.__cachingLogs = json.loads(content)
                else:
                    self.__cachingLogs = {'hit': 0, 'missed': 0}

    def __saveBanningLogs(self) -> None:
        if self.__banningLogFile:
            with open(self.__banningLogFile, 'w+') as f:
                f.write(json.dumps(self.__banningLogs))

    def __saveCachingLogs(self) -> None:
        if self.__cachingLogFile:
            with open(self.__cachingLogFile, 'w+') as f:
                f.write(json.dumps(self.__cachingLogs))


    def start(self) -> None:
        self.__loadBannedDomains()
        self.__loadBanningLogs()
        self.__loadCachingLogs()

        try:
            while True:
                if self.__verbose:
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

                if self.__verbose:
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

                    # when a banning log file is provided, the
                    # banning log dictionary must be updated
                    if self.__banningLogFile:
                        if domainName in self.__banningLogs:
                            self.__banningLogs[domainName] += 1
                        else:
                            self.__banningLogs[domainName] = 1

                    if self.__verbose:
                        print(f'blocked!')
                else:
                    resolvedIP = self.__solver.getFromCache(domainName)
                    # requested domain name was stored in cache
                    if resolvedIP:
                        # cache logging was enabled
                        if self.__cachingLogFile:
                            self.__cachingLogs['hit'] += 1

                        if self.__verbose:
                            print(f'got: "{resolvedIP}"')

                    # domain name cache expired or doesn't exist
                    else:
                        resolvedIP = self.__solver.recursivelyResolveDomain(domainName)

                        # domain could be resolved
                        if resolvedIP:
                            self.__solver.putInCache(domainName, resolvedIP)

                            # caching logging is enabled
                            if self.__cachingLogFile:
                                self.__cachingLogs['missed'] += 1

                            if self.__verbose:
                                print(f'got: "{resolvedIP}"')

                        # domain name could not be resolved
                        else:
                            if self.__verbose:
                                print('failed to resolve!')

                            dnsResponse.rcode = 3      # domain could not be resolved
                            self.__mainSocket.sendto(bytes(dnsResponse), clientAddress)
                            continue

                dnsResponse.rcode = 0      # response is successful
                dnsResponse.an = DNSRR(
                        rrname=domainName,
                        type='A',
                        rclass='IN',
                        rdata=resolvedIP,
                        ttl=self.__defaultTTL
                    )

                self.__mainSocket.sendto(bytes(dnsResponse), clientAddress)
        # executed after either process signals are treated;
        # used to silence exception messages
        except:
            pass

    # method used to gracefully halt the execution whenever
    # SIGTERM or SIGINT are sent to the process;
    # the two unused arguments are required by the signal module
    def __stop(self, signalNumber, stackFrame):
        # all in-memory logs are written to the associated file
        self.__saveBanningLogs()
        self.__saveCachingLogs()
        # the socket is gracefully closed
        self.__mainSocket.close()

        if self.__verbose:
            print('[*] goodbye!')



parser = argparse.ArgumentParser(
    description='Local Recursive DNS Resolver with built-in caching and ad blocking.',
    epilog='Built with scapy.'
)

parser.add_argument('-i', '--ip-address', default='127.0.0.1', type=str, dest='ipAddress', help='loopback address on which the server should start; defaults to 127.0.0.1', metavar='IP-ADDRESS')
parser.add_argument('-r', '--root-server', required=True, type=str, dest='rootServer', help='IPv4 address of the root DNS server from which every recursive lookup starts', metavar='ROOT-SERVER')
parser.add_argument('-b', '--banned-domains-file', required=True, type=str, dest='bannedDomainsFile', help='text file containing a banned domain name on each line', metavar='BANNED-DOMAINS-FILE')
parser.add_argument('-t', '--ttl', default=3600, type=int, dest='defaultTTL', help='amount of time (in seconds) for which resolved domains will be cached; defaults to 3600', metavar='TTL')
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='log the resolving process in the console in real-time')
parser.add_argument('-lb', '--log-banned-domains', required=False, type=str, dest='banningLogFile', help='log the number of requests for each banned domain in a json file, which must be provided', metavar='LOG-BANNED-DOMAINS')
parser.add_argument('-lc', '--log-caching', required=False, type=str, dest='cachingLogFile', help='log the number of hits and the number of misses of the built-in cache in a json file, which must be provided', metavar='LOG-CACHING')

arguments = parser.parse_args()


server = Main(arguments.ipAddress, arguments.rootServer, arguments.bannedDomainsFile, arguments.defaultTTL, arguments.verbose, arguments.banningLogFile, arguments.cachingLogFile)
server.start()
