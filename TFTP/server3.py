#!/usr/bin/env python3
import argparse
import select
import struct
import socket
import sys
import threading
import queue
from datetime import datetime
from datetime import timedelta

HOST = ''
PORT = 6969
parser = argparse.ArgumentParser()
parser.add_argument('--host', default=HOST)
parser.add_argument('--port', type=int, default=PORT)
args = parser.parse_args()
clients = dict()
epoll = select.epoll()
alpha = 1/8
beta = 1/4
K = 4
G = 1000

class CyclicBufferIterator:
    def __init__(self, buf):
        self.buf = buf
        self.index = buf.start
        self.iterated = -1
    def __next__(self):
        if self.iterated == (self.buf.amount-1):
            raise StopIteration
        self.iterated += 1
        return self.buf.tab[(self.buf.start+self.iterated)%self.buf.size]

class CyclicBuffer:
    def __init__(self, size):
        self.size = size
        self.start = 0
        self.amount = 0
        self.tab = [None]*size
    def add(self, a):
        if self.amount==self.size:
            return
        self.tab[(self.start+self.amount)%self.size] = a
        self.amount += 1
    def remove(self):
        if self.amount==0:
            return
        self.start += 1
        self.start = self.start%self.size
        self.amount -= 1
    def remove(self, a):
        if a > self.amount:
            a = self.amount
        self.start += a
        self.start = self.start%self.size
        self.amount -= a
    def last(self):
        if self.amount==0:
            return None
        return self.tab[(self.start+self.amount-1)%self.size]
    def full(self):
        return self.amount==self.size
    def empty(self):
        return self.amount==0
    def __iter__(self):
        return CyclicBufferIterator(self)
    
class Client:
    RTO = 5000
    SRTT = -1
    RTTVAR = -1
    def __init__(self, blocksize, windowsize, addr, sock, file1, timestamp):
        self.blocksize = blocksize
        self.addr = addr
        self.sock = sock
        self.timestamp = timestamp
        self.windowsize = windowsize
        self.comm = CyclicBuffer(windowsize)
        self.file1 = file1
        self.blocknum = 0
    def send_buf(self):
        for ans in self.comm:
            self.sock.sendto(ans, self.addr)
            self.timestamp = datetime.now()
        
        
def parse_options(data):
    windowsize = 1
    blocksize = 512
    while len(data)>0:
        option = data[:data.index(b'\x00')].decode('utf-8')
        data = data[data.index(b'\x00')+1:]
        value = int.from_bytes(data[:2], "big")
        data = data[2:]
        data = data[data.index(b'\x00')+1:]
        if option == 'blksize' and value*8 != 512:
            blocksize = value*8
        if option == 'windowsize' and value != 1:
            windowsize = value
    return blocksize, windowsize

def build_accept_options():
    global windowsize, blocksize
    accept_options = b''
    if blocksize != 512:
        accept_options += str.encode('blksize')+bytes.fromhex('00')+int(blocksize/8).to_bytes(2, "big")+bytes.fromhex('00')
    if windowsize != 1:
        accept_options += str.encode('windowsize')+bytes.fromhex('00')+windowsize.to_bytes(2, "big")+bytes.fromhex('00')
    return accept_options
    

def deal_with_new_client():
    global blocksize, windowsize, clients, epoll
    data, addr = server_sock.recvfrom(65000)
    #this fixes error that occured in tests, shouldn't be necessary in real life situation
    old = [k for (k, v) in clients.items() if v.addr == addr]
    for k in old:
        del clients[k]
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    epoll.register(client_sock.fileno(), select.EPOLLIN)
    opcode = int.from_bytes(data[0:2], "big")
    if opcode != 1:
        error_msg = (5).to_bytes(2, 'big')+(0).to_bytes(2, 'big')+str.encode("error")+(0).to_bytes(2, 'big')
        client_sock.sendto(error_msg, addr)
        epoll.unregister(fileno)
        del clients[fileno]
        return
    filename = data[2:(data[2:].index(b'\x00')+2)].decode("utf-8")
    data = data[(data[2:].index(b'\x00')+2)+1:]
    data = data[data.index(b'\x00')+1:]
    blocksize, windowsize = parse_options(data)
    accept_options = build_accept_options()
    clients[client_sock.fileno()] = Client(blocksize, windowsize, addr, client_sock, open(filename, 'rb'), datetime.now())
    client = clients[client_sock.fileno()]
    if accept_options != b'':
        accept_options = (6).to_bytes(2, "big")+accept_options
        client_sock.sendto(accept_options, addr)
        client.timestamp = datetime.now()
        client.comm.add(accept_options)
        client.blocknum = 0
        for i in range(1, client.windowsize):
            content = client.file1.read(client.blocksize)
            if content==b'':
                return
            ans = (3).to_bytes(2, 'big')+(client.blocknum+i).to_bytes(2, 'big')+content
            client_sock.sendto(ans, addr)
            client.comm.add(ans)
            client.timestamp = datetime.now()
    else:
        client.blocknum = 0
        for i in range(1, client.windowsize+1):
            content = client.file1.read(client.blocksize)
            if content==b'':
                return
            ans = (3).to_bytes(2, 'big')+(client.blocknum+i).to_bytes(2, 'big')+content
            client_sock.sendto(ans, addr)
            client.comm.add(ans)
            client.timestamp = datetime.now()
def deal_with_old_client(fileno):
    global blocksize, windowsize, clients, epoll
    client = clients[fileno]
    sock = client.sock
    data, addr = sock.recvfrom(65000)
    current_time = datetime.now()
    ping = int(((current_time-client.timestamp)/timedelta(microseconds=1))/1000)
    if client.SRTT == -1 and client.RTTVAR == -1:
            client.SRTT = ping
            client.RTTVAR = ping/2
    else:
        client.RTTVAR = (1 - beta) * client.RTTVAR + beta * abs(client.SRTT - ping)
        client.SRTT = (1 - alpha) * client.SRTT + alpha * ping
    client.RTO = client.SRTT + max (G, K*client.RTTVAR)
    opcode = int.from_bytes(data[0:2], "big")
    if opcode != 4:
        print("abandoning")
        error_msg = (5).to_bytes(2, 'big')+(0).to_bytes(2, 'big')+str.encode("error")+(0).to_bytes(2, 'big')
        sock.sendto(error_msg, addr)
        del clients[fileno]
        epoll.unregister(fileno)
        return       
    block_num_rec = int.from_bytes(data[2:4], "big")
    client.comm.remove((block_num_rec - client.blocknum+1)%65535)
    client.blocknum = block_num_rec+1 
    client.blocknum = client.blocknum%65535
    if not client.comm.empty():
        new_start = int.from_bytes(client.comm.last()[2:4], "big")+1
        new_start = new_start%65535
    else:
        new_start = client.blocknum
    while not client.comm.full():
        content = client.file1.read(client.blocksize)
        if content==b'':
            break
        else:
            client.comm.add((3).to_bytes(2, 'big')+(new_start).to_bytes(2, 'big')+content)
            new_start += 1
            new_start = new_start%65535
    client.timestamp = datetime.now()
    if client.comm.empty():
        epoll.unregister(fileno)
        del clients[fileno]
        return
    client.send_buf()


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
    server_sock.bind( (args.host, args.port) )
    epoll.register(server_sock.fileno(), select.EPOLLIN)
    while True:
        for fileno, event in epoll.poll(timeout=0.1):
            if fileno == server_sock.fileno() and event & select.EPOLLIN:
                deal_with_new_client()
                continue
            elif fileno in clients and event & select.EPOLLIN:
                deal_with_old_client(fileno)
                continue
        timed_out_clients = [v for (k, v) in clients.items() if v.timestamp+timedelta(microseconds = v.RTO*1000)<datetime.now()]
        for client in timed_out_clients:
            client.send_buf()
