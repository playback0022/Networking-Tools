import socket
import argparse
import time


parser = argparse.ArgumentParser(
    description='Script meant to simulate the behaviour of a server in communication with a client, '
                'via an IPv4 TCP socket. The message received from any connected clients will be '
                'logged to the screen and, in return, the specified message will be sent sent back. '
                'This process continues indefinitely, with a pause of "timeout" seconds inbetween the '
                'sending and the receiving.'
)

parser.add_argument('-p', '--port', required=True, type=int, help='the port on which the server should listen')
parser.add_argument('-m', '--message', default='hello to you, too!', type=str, help='what shall be sent to the client?')
parser.add_argument('-t', '--timeout', default=5, type=int, help='the pause between the sending and the receiving')

arguments = parser.parse_args()

if arguments.port <= 0 or arguments.timeout <= 0 or arguments.clients <= 0:
    raise Exception('Number of clients, port and timeout must be positive integers!')


print('[*] Socket initiated...')

# declaring the socket type (IPv4) and the protocol which will be used to send messages (TCP)
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
serverAddress = ('', arguments.port)    # the socket will be bound to any available interface

try:
    serverSocket.bind(serverAddress)            # socket becomes a 'server' socket
    print('[*] Socket bound successfully.')
    # this script is intended for a single client-server
    # connection (the server handles at most one client)
    serverSocket.listen(1)
    print('[*] Listening...')
    connection, address = serverSocket.accept()
    print(f'[*] Handshake successful.')
    print(f'Connection established with: {address[0]}:{address[1]}.')

    # the resulting 'connection' is now used to communicate with the client
    while True:
        # the server accepts messages of at most 1 Kb in size
        receivedData = connection.recv(1024)
        print(f'[*] Received: "{receivedData}"')
        time.sleep(arguments.timeout)

        connection.send(arguments.message)
        print('[*] Message sent.')
        time.sleep(arguments.timeout)
# gracefully closing the socket
except KeyboardInterrupt:
    print('[*] Closing socket...')
    serverSocket.close()
    print('[*] Goodbye!')
