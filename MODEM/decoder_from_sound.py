#!/usr/bin/env python3
 
import pyaudio
import wave
import sys
import numpy as np
import struct
import copy
import time
from bitarray import bitarray



if len(sys.argv) < 3:
    print("Decodes a message.\n\nUsage: %s freq low (int) freq high (int) - recommended 1000 and 2000" % sys.argv[0])
    sys.exit(-1)
    
freqlow = int(int(sys.argv[1])/100)
freqhigh = int(int(sys.argv[2])/100)

def bb2(x):
    if x==bitarray('11110'):
           return bitarray('0000')
    if x==bitarray('01001'):
           return bitarray('0001')
    if x==bitarray('10100'):
           return bitarray('0010')
    if x==bitarray('10101'):
           return bitarray('0011')
    if x==bitarray('01010'):
           return bitarray('0100')
    if x==bitarray('01011'):
           return bitarray('0101')
    if x==bitarray('01110'):
           return bitarray('0110')
    if x==bitarray('01111'):
           return bitarray('0111')
    if x==bitarray('10010'):
           return bitarray('1000')
    if x==bitarray('10011'):
           return bitarray('1001')
    if x==bitarray('10110'):
           return bitarray('1010')
    if x==bitarray('10111'):
           return bitarray('1011')
    if x==bitarray('11010'):
           return bitarray('1100')
    if x==bitarray('11011'):
           return bitarray('1101')
    if x==bitarray('11100'):
           return bitarray('1110')
    if x==bitarray('11101'):
           return bitarray('1111')

def decode_4b5b(a):
    b = bitarray()
    while len(a)>0:
        b += bb2(a[0:5])
        a = a[5:]
    return b

def decode_nrzi(a):
    prev = True
    b = bitarray()
    for i in range(0, len(a)):
        if(a[i] == prev):
            b.append(False)
        else:
            b.append(True)
        prev = a[i]
    return b

def div(c, b):
    a = copy.deepcopy(c)
    while not a[0]:
        a.remove('')
    while not b[0]:
        b.remove('')
    d = bitarray()
    d += max((len(a)-len(b)+1), 0) * bitarray([False])
    max_diff = len(a)-len(b)+1
    d.setall(False)
    while len(a)>=len(b):
        diff = len(a) - len(b)
        d[max_diff-1-diff] = True
        c = b + diff * bitarray([False])
        a = ~(a ^ ~c)
        while not a[0]:
            a.remove('')
    return d, a;
        
def crc32(e):
    a = copy.copy(e)
    a += 32 * bitarray([False])
    b = div(a, bitarray('100000100110000010001110110110111'))[1]
    c = bitarray()
    if(len(b)<32):
        c += (32-len(b))*bitarray([False])
    c += b
    return c

def nextNumber():
    data = stream.read(CHUNK)
    data_val = []
    if not data:
        return False
    for i in range (CHUNK):
        data_val.append(struct.unpack('h', b"".join([data[(2*i):(2*i+2)]]))[0])
    arr = np.array(data_val)
    fourier = np.fft.rfft(arr, CHUNK)
    fourier = np.abs(fourier)
    hz = np.argmax(fourier)*(44000//CHUNK)
    return hz>(freqlow*(44000//CHUNK)+freqhigh*(44000//CHUNK))*0.6

CHUNK = 440
sample_format = pyaudio.paInt16
pa = pyaudio.PyAudio()

stream = pa.open(format=sample_format,
                channels=1,
                rate=44000,
                frames_per_buffer=CHUNK,
                input=True)

while True:
    b = bitarray()
    msg = bitarray()
    crc = bitarray()
    while True:
        data = stream.read(CHUNK)
        data_val = []
        if not data:
            break
        for i in range (CHUNK):
            data_val.append(struct.unpack('h', b"".join([data[(2*i):(2*i+2)]]))[0]/2**15)
        arr = np.array(data_val)
        fourier = np.fft.rfft(arr, CHUNK)
        fourier = np.abs(fourier)
        hz = np.argmax(fourier)
        if(fourier[freqlow]>fourier[freqhigh]+10):
            break
        else:
            data = stream.read(int(CHUNK/20))

    prev = False
    while True:
        one = nextNumber()
        if prev and one:
            break
        else:
            prev = one
    for i in range (0, 140):
        b.append(nextNumber())
    org = b
    b = decode_nrzi(b)
    b = decode_4b5b(b)
    c = struct.unpack("!H", b[96:])[0]
    for i in range (0, c*10):
        msg.append(nextNumber())
    for i in range (0, 40):
        crc.append(nextNumber())


    whole = org + msg + crc
    whole = decode_nrzi(whole)
    whole = decode_4b5b(whole)
    crc = whole[-32:]
    whole = whole[:-32]
    msg = whole[-c*8:]
    if crc32(b+msg) == crc:
        print("Control sum checks out.")
    else:
        print("Control sum doesn't check out. Abandoning")
        print(crc32(b+msg))
        print(crc)
        
    print("Destination:")
    print(struct.unpack("!HL", b[0:48])[1])
    print("Source:")
    print(struct.unpack("!HL", b[48:96])[1])
    print("Message:")
    print(msg.tobytes().decode('utf-8'))

    
