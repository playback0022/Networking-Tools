import os
from scapy.all import *
from netfilterqueue import NetfilterQueue as nfq
import argparse


def extractPacket(packet):
    capturedBytes = packet.get_payload()
    convertedPacket = IP(capturedBytes)
    convertedPacket.show()
    # the IP packet object contains a TCP packet against which
    # some validations should be made (only PUSH, not SYN/ACK);
    # after the validations, the message should be altered via
    # the 'alterPacket' function and accepted;
    # furthermore, we should probably accept all packages with
    # other source or destination IPs than those of the targets


def alterPacket(packet):
    pass


parser = argparse.ArgumentParser(
    description='Script used in man-in-the-middle attacks, which captures IP datagrams meant to be '
                'forwarded from a target host to another and, in the case of those containing a TCP '
                'segment, alters their content by appending the provided message to the existing payload. '
)

# exactly 2 arguments expected for the 'victim' flag (the two targets); the name
# of each argument used in the auto-generated help menu is described by 'metavar'
parser.add_argument('-v', '--victims', nargs=2, required=True, type=str, dest='victims',
                    help='the IPs of the two target hosts', metavar='VICTIM')
parser.add_argument('-m', '--message', default=' bad machine, bad!', type=str, help='what shall be appended to the captured payloads?')

arguments = parser.parse_args()


print('[*] Initializing packet queue...')
packetQueue = nfq()

try:
    # only packets meant for forwarding should be captured,
    # since it is only among these were the communication
    # between the two targets takes place;
    # 17 is a prime number, so it should do nicely as a queue number
    os.system('iptables -I FORWARD -j NFQUEUE --queue-num 17')
    print('[*] IP tables updated successfully.')

    packetQueue.bind(17, extractPacket)
    print('[*] Packet queue bound successfully.')
    packetQueue.run()
except KeyboardInterrupt:
    print('[*] Unbinding queue...')
    packetQueue.unbind()

    print('[*] Resetting IP table rules...')
    os.system('iptables --flush')

    print('[*] Goodbye!')
