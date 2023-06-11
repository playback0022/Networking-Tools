import socket
import argparse
import time


parser = argparse.ArgumentParser(
    description='Script meant to simulate the behaviour of a client in communication with a server, '
                'via an IPv4 TCP socket. Based on the provided IP address and port number, the '
                'specified message will be sent to the server and, in return, the message received '
                'from the server will be logged to the screen. This process continues indefinitely, '
                'with a pause of "timeout" seconds inbetween the sending and the receiving.'
)

parser.add_argument('-ip', '--ip-address', required=True, type=str, dest='ipAddress', help='the IP address of the server')
parser.add_argument('-p', '--port', required=True, type=int, help='the port on which the server is listening')
parser.add_argument('-m', '--message', default='hi there!', type=str, help='what shall be sent to the server?')
parser.add_argument('-t', '--timeout', default=5, type=int, help='the pause between the sending and the receiving')

arguments = parser.parse_args()

if arguments.port <= 0 or arguments.timeout <= 0:
    raise Exception('Port and timeout must be positive integers!')


print('[*] Socket initiated...')

# declaring the socket type (IPv4) and the protocol which will be used to send messages (TCP)
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
serverAddress = (arguments.ipAddress, arguments.port)

try:
    clientSocket.connect(serverAddress)     # socket becomes a 'client' socket
    print('[*] Handshake successful. Connection established.')

    while True:
        clientSocket.send(arguments.message.encode('utf-8'))
        print('[*] Message sent.')

        # the client accepts messages of at most 1 Kb in size
        receivedData = clientSocket.recv(1024)
        print(f'[*] Received: "{receivedData}"')
        time.sleep(arguments.timeout)
# gracefully closing the socket
except KeyboardInterrupt:
    print('[*] Closing socket...')
    clientSocket.close()
    print('[*] Goodbye!')
