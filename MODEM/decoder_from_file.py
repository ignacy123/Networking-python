#!/usr/bin/env python3
 
import pyaudio
import wave
import sys
import numpy as np
import struct
import copy
from bitarray import bitarray

if len(sys.argv) < 2:
    print("Decodes a file.\n\nUsage: %s filename.wav" % sys.argv[0])
    sys.exit(-1)

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

def decode(a):
    a = a[64:]
    a = decode_nrzi(a)
    a = decode_4b5b(a)
    crc = a[-32:]
    a = a[:-32]
    crc_new = crc32(a)
    if crc==crc_new:
        print("Control sum checks out")
    else:
        print("Control sum doesn't check out. Abandoning")
        return
    print("Source: ")
    print(struct.unpack("!HL", a[0:48])[1])
    a = a[48:]
    print("Destination: ")
    print(struct.unpack("!HL", a[0:48])[1])
    a = a[48:]
    size = struct.unpack("!H", a[:16])[0]
    a = a[16:]
    print("Message: ")
    print(a.tobytes().decode('utf-8'))

CHUNK = 4400
 
wf = wave.open(sys.argv[1], 'rb')
 
pa = pyaudio.PyAudio()

bits = bitarray()
 
stream = pa.open(
            output=True,
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            format=pa.get_format_from_width(wf.getsampwidth()),
        ) 
 
freq = [] 
while True:
    data = wf.readframes(CHUNK)
    data_val = []
    if not data:
        break
    for i in range (CHUNK):
        data_val.append(struct.unpack('h', b"".join([data[(2*i):(2*i+2)]]))[0])
    arr = np.array(data_val)
    fourier = np.fft.rfft(arr, CHUNK)
    fourier = np.abs(fourier)
    freq.append(np.argmax(fourier)*10)
bigger = max(freq)
print(freq)
for i in range(len(freq)):
    if(freq[i]==bigger):
        bits.append(True)
    else:
        bits.append(False)

stream.stop_stream()
stream.close()
pa.terminate()
decode(bits)
