#!/usr/bin/env python3

from bitarray import bitarray
import struct
import copy
import pyaudio
import wave
import numpy as np
import struct
import sys

chunk = 440
sample_format = pyaudio.paInt16  # 16 bits per sample

def bb(x):
    if x==bitarray('0000'):
           return bitarray('11110')
    if x==bitarray('0001'):
           return bitarray('01001')
    if x==bitarray('0010'):
           return bitarray('10100')
    if x==bitarray('0011'):
           return bitarray('10101')
    if x==bitarray('0100'):
           return bitarray('01010')
    if x==bitarray('0101'):
           return bitarray('01011')
    if x==bitarray('0110'):
           return bitarray('01110')
    if x==bitarray('0111'):
           return bitarray('01111')
    if x==bitarray('1000'):
           return bitarray('10010')
    if x==bitarray('1001'):
           return bitarray('10011')
    if x==bitarray('1010'):
           return bitarray('10110')
    if x==bitarray('1011'):
           return bitarray('10111')
    if x==bitarray('1100'):
           return bitarray('11010')
    if x==bitarray('1101'):
           return bitarray('11011')
    if x==bitarray('1110'):
           return bitarray('11100')
    if x==bitarray('1111'):
           return bitarray('11101')
    

def plain_to_4b5b(a):
    b = bitarray()
    if len(a)%4 != 0:
        a += (4-len(a)%4)*bitarray('0')
    while len(a)>0:
        b += bb(a[0:4])
        a = a[4:]
    return b

def nrzi(a):
    b = bitarray()
    prev = True
    for i in range(0, len(a)):
        if a[i]:
            prev = not prev
            b.append(prev)
        else:
            b.append(prev)
    return b

def a4b5b_nrzi(a):
    return nrzi(plain_to_4b5b(a))

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

def encode(src, dst, msg):
    a = bitarray()
    a.frombytes(struct.pack("!HL", 0, src))
    a.frombytes(struct.pack("!HL", 0, dst))
    a.frombytes(struct.pack("!H", len(msg)));
    a.frombytes(msg)
    c = crc32(a);
    a += c
    preamble = bitarray('1010101010101010101010101010101010101010101010101010101010101011');
    a = a4b5b_nrzi(a)
    a = preamble + a;
    return(a)
    
def record(a, freqlow, freqhigh):
    pa = pyaudio.PyAudio()  
    frames = [] 
    for i in range(0, len(a)):
        if(a[i]):
            data = b''.join([struct.pack('h', int(np.sin(i/int(44000/int(freqhigh)) * 2 * np.pi) * (2**15-1))) for i in range(chunk)])
        else:
            data = b''.join([struct.pack('h', int(np.sin(i/int(44000/int(freqlow)) * 2 * np.pi) * (2**15-1))) for i in range(chunk)])
        frames.append(data)
    
    stream = pa.open(
            output=True,
            channels=1,
            rate=44000,
            format=sample_format,
        ) 
    for data in frames:
        stream.write(data)
        
    # Terminate the PortAudio interface
    pa.terminate()
    # Save the recorded data as a WAV file
    #wf = wave.open(filename, 'wb')
    #wf.setnchannels(1)
    #wf.setsampwidth(p.get_sample_size(sample_format))
    #wf.setframerate(44000)
    #wf.writeframes(b''.join(frames))
    #wf.close()

def transmit(src, dst, msg, freqlow, freqhigh):
    a = encode(src, dst, msg)
    record(a, freqlow, freqhigh)

if len(sys.argv) < 6:
    print("Transmits a message.\n\nUsage: %s destination(int) source(int) message(string) freqlow freqhigh" % sys.argv[0])
    sys.exit(-1)
    

transmit(int(sys.argv[1]), int(sys.argv[2]), bytes(sys.argv[3], 'utf-8'), sys.argv[4], sys.argv[5])
