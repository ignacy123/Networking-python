#!/usr/bin/env python3
import argparse
import struct
import socket
import sys
from datetime import datetime
from datetime import timedelta

HOST = ''
PORT = 6969
MODE = 'octet'
parser = argparse.ArgumentParser()
parser.add_argument('--host', default=HOST)
parser.add_argument('--port', type=int, default=PORT)
parser.add_argument('--blksize', type=int, default=64)
parser.add_argument('--windowsize', type=int, default=1)
parser.add_argument('--filename', default = 'a')
args = parser.parse_args() 
port = args.port
blocksize = 512
windowsize = 1
comm = [None]
ts = datetime.now()
ts2 = ts
first_missing = 0
block_num = 1
alpha = 1/8
beta = 1/4
SRTT = -1
RTTVAR = -1
RTO = 500
K = 4
G = 200
file1 = open(args.filename, "w+")

def parse_options(data):
    global blocksize, windowsize
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

def do_one_round(sock):
    global port, windowsize, blocksize, comm, ts, ts2, first_missing, block_num
    finished = False
    received_opt = False
    while True:
            try:
                data, addr = sock.recvfrom(65000)
            except:
                break
            if ts==ts2:
                ts2 = datetime.now()
            port = addr[1]
            opcode = int.from_bytes(data[0:2], "big")
            data = data[2:]
            if opcode == 6:
                blocksize, windowsize = parse_options(data)
                comm = [None]*windowsize
                received_opt = True
                if windowsize==1:
                    break
            elif opcode == 3:
                block_num_rec = int.from_bytes(data[0:2], "big")
                data = data[2:]
                comm[(block_num_rec-block_num)%65535] = data
                if ((block_num_rec-block_num)%65535)==first_missing:
                    #shifting first missing, this could be an old packet fixing some early hole
                    while first_missing<windowsize and comm[first_missing] != None:
                        first_missing += 1
                    if len(data)<blocksize:
                        finished = True
                        break
                if first_missing == windowsize:
                    break
                if first_missing == windowsize-1 and received_opt:
                    break
            else:
                print("error")
                sock.close()
                sys.exit("error")
    return finished
    

ans = (1).to_bytes(2, 'big')+str.encode(args.filename)+bytes.fromhex('00')+str.encode(MODE)+bytes.fromhex('00')
if args.blksize != 64:
    ans += str.encode("blksize")+bytes.fromhex('00')+args.blksize.to_bytes(2, 'big')+bytes.fromhex('00')
if args.windowsize != 1:
    ans += str.encode("windowsize")+bytes.fromhex('00')+args.windowsize.to_bytes(2, 'big')+bytes.fromhex('00')
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    done = False
    while True:
        ts = datetime.now()
        ts2 = ts
        first_missing = 0
        sock.settimeout(RTO/1000)
        sock.sendto(ans, (args.host, port))
        if done:
            break
        done = do_one_round(sock)
        for i in range(0, first_missing):
            file1.write(comm[i].decode('utf-8'))
        comm = [None]*windowsize
        ans = (4).to_bytes(2, 'big')+((block_num+first_missing-1)%65535).to_bytes(2, 'big')
        print("sending ack", (block_num+first_missing-1)%65535)
        block_num += first_missing
        block_num = block_num%65535
        ping = int(((ts2-ts)/timedelta(microseconds=1))/1000)
        print("ping: ", ping, "ms")
        if SRTT == -1 and RTTVAR == -1:
            SRTT = ping
            RTTVAR = ping/2
        else:
            RTTVAR = (1 - beta) * RTTVAR + beta * abs(SRTT - ping)
            SRTT = (1 - alpha) * SRTT + alpha * ping
        RTO = SRTT + max (G, K*RTTVAR)
file1.close()
            
    
