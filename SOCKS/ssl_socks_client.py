#!/usr/bin/env python3
import socket
import ssl
SOCKS = ('azure.buczek.ninja', 8080)
HOST = 'satori.tcs.uj.edu.pl'
PORT = 80
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(SOCKS)
context = ssl.create_default_context()
sock = context.wrap_socket(sock, server_hostname=SOCKS[0])
readfile = sock.makefile('rb')
writefile = sock.makefile('wb')
#writefile.write(b'CONNECT ' + bytes(SOCKS[0], 'utf8') + b' ' + bytes(str(SOCKS[1]), 'utf8')+b'\r\n')
writefile.write(b'CONNECT ' + bytes(SOCKS[0], 'utf8') + b' ' + bytes(str(SOCKS[1]), 'utf8')+b'\r\n')
writefile.write(b'CONNECT ' + bytes(HOST, 'utf8') + b' ' + bytes(str(PORT), 'utf8')+b'\r\n')
req = b'\r\n'.join([
    b'GET / HTTP/1.0',
    b'Host: ' + bytes(HOST, 'utf8'),
    b'Connection: close',
    b'',
    b''
    ])
print(req)
writefile.write(req)
writefile.close()
print(readfile.read())
readfile.close()
sock.close()
