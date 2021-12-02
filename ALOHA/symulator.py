#!/usr/bin/env python3
import argparse
import os
import pwd
import socket
import struct
import sys
import threading
import time
import traceback
import random
import queue

PATH = '/tmp/aloha.socket'
parser = argparse.ArgumentParser()
parser.add_argument('--path', default=PATH)
parser.add_argument('--continous', type=bool, default=False)
parser.add_argument('--slot', type=float, default=0.25)
parser.add_argument('--slots', type=float, default=100)
parser.add_argument('--clients', type=int, default=5)
parser.add_argument('--packetprobability', type=float, default=0.5)
parser.add_argument('--firstinterval', type=int, default=1)
parser.add_argument('--multiplier', type=int, default=2)
args = parser.parse_args()

close = False
clients = list()
clients_lock = threading.Lock()
busy = False
finished = False

def Handler(client_sock, result):
    try:
        with client_sock:
            if result:
                client_info = client_sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
                client_pid, client_uid, client_gid = struct.unpack('3i', client_info)
                #print('Accept {}'.format(pwd.getpwuid(client_uid).pw_gecos.split(',')[0].split(' ')[-1]))
                client_sock.sendall(b'0x01')
            else:
                client_sock.sendall(b'0x00')
    except:
        pass

def Timer(server_sock):
    global finished
    slots = 0
    while not close and slots<(args.slots+2):
        time.sleep(args.slot)
        slots = slots+1
        with clients_lock:
            for client_sock in clients:
                threading.Thread(target=Handler, args=(client_sock, len(clients)==1)).start()
            clients.clear()
    finished = True
    print("timer done")
    server_sock.shutdown(socket.SHUT_RDWR)
    server_sock.close()


def slotted_server():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server_sock:
            timer = threading.Thread(target=Timer, args = (server_sock, ))
            timer.start()
            try:
                os.unlink(args.path)
            except:
                pass
            server_sock.bind(args.path)
            os.chmod(args.path, 0o777)
            server_sock.listen(1)
            while timer.is_alive():
                try:
                    client_sock, _ = server_sock.accept()
                    with clients_lock:
                        clients.append( client_sock )
                except:
                    pass
    except:
        traceback.print_exc()
        close = True
        
def communicate():
    time.sleep(args.slot)

def continous_handler(client_sock):
    global busy
    t2 = threading.Thread(target=communicate)
    t2.start()
    try:
        with client_sock:
            while busy:
                if not t2.is_alive():
                    busy = False
                    client_sock.sendall(b'0x01')
                    client_sock.close()
                    return
            busy = False    
            client_sock.sendall(b'0x00')
            client_sock.close()   
            
    except:
        busy = False
        pass
        
def party_spoiler(server_sock):
    time.sleep((args.slots+2)*args.slot)
    server_sock.shutdown(socket.SHUT_RDWR)
    server_sock.close()

def continous_server():
    global busy
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server_sock:
            timer = threading.Thread(target=party_spoiler, args = (server_sock, ))
            timer.start()
            try:
                os.unlink(args.path)
            except:
                pass
            server_sock.bind(args.path)
            os.chmod(args.path, 0o777)
            server_sock.listen(1)
            while timer.is_alive():
                try:
                    client_sock, _ = server_sock.accept()
                    if busy:
                        client_sock.sendall(b'0x00')
                        client_sock.close()
                        busy = False
                    else:
                        busy = True
                        t1 = threading.Thread(target=continous_handler, args=(client_sock, ))
                        t1.start()
                except:
                    pass
                
    except:
        traceback.print_exc()
        close = True

def client():
    packets_sent = 0
    summaric_delay = 0
    actual_backoff = 0
    prev = 0
    while True:
        if random.random()>args.packetprobability:
            time.sleep(args.slot)
            continue
        connected = False
        backoff = args.firstinterval
        while not connected:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                try:
                    s.connect(args.path)
                except:
                    summaric_delay -= actual_backoff
                    print("sent ", packets_sent, " packets")
                    print("total delay was ", summaric_delay)
                    print("last max backoff was: ", backoff)
                    return packets_sent, summaric_delay
                #s.sendall(b'Hello, world')
                while True:
                    if finished:
                        break
                    try:
                        data = s.recv(1024)
                    except:
                        break
                    #print(data)
                    if not data:
                        break
                    if(data == b'0x00'):
                        #print('Rejected :<', repr(data))
                        actual_backoff = random.randrange(backoff)
                        summaric_delay += actual_backoff
                        print("rejected, waiting for: ", actual_backoff)
                        backoff = backoff*args.multiplier
                        time.sleep(actual_backoff*args.slot)
                        break
                    elif(data == b'0x01'):
                        #print('Accepted :>', repr(data))
                        packets_sent = packets_sent+1
                        connected = True
                        break
        
if(not args.continous):
    print("starting slotted server")
    threading.Thread(target=slotted_server).start()
else:
    print("starting continous server")
    threading.Thread(target=continous_server).start()
time.sleep(args.slot*2)
que = queue.Queue()
threads = []
for i in range (0, args.clients):
    threads.append(threading.Thread(target=lambda q, arg1: q.put(client()), args=(que, 'world!')))
for i in range (0, args.clients):
    threads[i].start()
for i in range (0, args.clients):
    threads[i].join()
total_packets = 0
total_delay = 0
for i in range (0, args.clients):
    a, b = que.get()
    total_packets += a
    total_delay += b
print("total packets: ", total_packets)
print("packets per slot: ", float(total_packets/args.slots))
print("total delay: ", total_delay)
print("average delay (for successfully sent packets): ", float(total_delay/total_packets))
