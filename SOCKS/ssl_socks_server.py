 
#!/usr/bin/env python3
import argparse
import socket
import socketserver
import ssl
from threading import Thread
import time

 

HOST = ''
PORT = 8080
parser = argparse.ArgumentParser()
parser.add_argument('--host', default=HOST)
parser.add_argument('--port', type=int, default=PORT)
args = parser.parse_args()

 

def filecopy(rfile, wfile, rsock, wsock):
    try:
        while True:
            b = rfile.read1(65536)
            print(b)
            if not b:
                break
            wfile.write(b)
            wfile.flush()
    finally:
        try:
            rsock.shutdown(socket.SHUT_RD)
        except:
            pass
        try:
            wsock.shutdown(socket.SHUT_WR)
        except:
            pass
 

class Handler(socketserver.StreamRequestHandler):
    def proxy(self, conn):
        rfile = conn.makefile('rb')
        wfile = conn.makefile('wb')
        threadr = Thread(target=filecopy, args=(self.rfile, wfile, self.connection, conn))
        threadr.start()
        threadw = Thread(target=filecopy, args=(rfile, self.wfile, conn, self.connection))
        threadw.start()
        while threadr.is_alive() or threadw.is_alive():
            time.sleep(1)
        threadr.join()
        threadw.join()

 

    def handle(self):
        control_line = [str(a, 'utf8') for a in self.rfile.readline().strip().split() if a]
        if len(control_line) == 0:
            return
        print(control_line)
        mode = control_line[0].upper()
        if mode == 'CONNECT' and len(control_line) >= 3:
            target_host = control_line[1]
            target_port = int(control_line[2])
            with socket.create_connection((target_host, target_port)) as conn:
                if target_port == 443 or target_host == 'azure.buczek.ninja':
                    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    context.load_cert_chain(
                        certfile='/etc/letsencrypt/live/buczek.ninja/fullchain.pem',
                        keyfile='/etc/letsencrypt/live/buczek.ninja/privkey.pem'
                    )
                    conn = context.wrap_socket(conn)
                self.proxy(conn)

 

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

 

with Server((args.host, args.port), Handler) as server:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(
        certfile='/etc/letsencrypt/live/buczek.ninja/fullchain.pem',
        keyfile='/etc/letsencrypt/live/buczek.ninja/privkey.pem'
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
