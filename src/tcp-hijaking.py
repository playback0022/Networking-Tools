import os
from scapy.all import *
from netfilterqueue import NetfilterQueue as nfq


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


packetQueue = nfq()

try:
    # only packets meant for forwarding should be captured,
    # since it is only among these were the communication
    # between the two targets takes place
    os.system('iptables -I FORWARD -j NFQUEUE --queue-num 17')
    packetQueue.bind(17, extractPacket)
    packetQueue.run()
except KeyboardInterrupt:
    packetQueue.unbind()
    os.system('iptables --flush')
