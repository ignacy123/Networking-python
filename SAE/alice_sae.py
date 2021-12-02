#!/usr/bin/env python3

from hashlib import sha256
import math
import random
import socket
import sys

_xormap = {('0', '1'): '1', 
           ('1', '0'): '1', 
           ('1', '1'): '0', 
           ('0', '0'): '0'}

p=int("FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF", 16)

q = (p-1)//2

def mult(a, b):
    return (a*b)%p

def reverse_mult(a):
    return fast_pow(a, p-2)

def fast_pow(a, b):
    result = 1
    while b > 0:
        if b%2==1:
            result = mult(result, a)
        a = mult(a, a)
        b = b//2
    return result

def encrypt(a):
    return sha256(a.encode('utf-8')).hexdigest()

def hex_to_int(a):
    return int(a, 16)

def xor_bin(a, b):
    if len(a) < len(b):
        a, b = b, a
    b = ''.join('0' for i in range (len(a)-len(b))) + b
    return ''.join(_xormap[x, y] for x, y in zip(a, b))

def str_to_bin(a):
    return ''.join(format(ord(x), '08b') for x in a)

def int_to_bin(a):
    return bin(a)[2:]


def KDF(n, k, l):
    l = str_to_bin(l)
    k = str_to_bin(k)
    n_bin = int_to_bin(n)
    ret = ''
    counter = 1
    while len(ret)*4<n:
        counter_bin = int_to_bin(counter)
        part = xor_bin(xor_bin(xor_bin(k, counter_bin), l), n_bin)
        ret += encrypt(part)
        counter += 1
    ret_num = int(ret, 16)
    return ret_num >> ((counter-1) * 256 - n)


def generatePE(password, max_name, min_name):
    found = 0
    PE = 2
    counter = 1
    n = len(int_to_bin(p))+64
    while found==0 and counter<=10:
        base = encrypt(max_name+min_name+password+str(counter))
        temp = KDF(n, base, "projekt SAE z sieci")
        seed = temp % (p-1) + 1
        temp = fast_pow(seed, 2)
        if (temp > 1):
            if found == 0:
                PE = temp
                found = 1
        counter += 1
    return PE

def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, 'big')
    
def int_from_bytes(xbytes: bytes) -> int:
    return int.from_bytes(xbytes, 'big')

if len(sys.argv) < 2:
    print("Usage: %s password" % sys.argv[0])
    sys.exit(-1)
    

PW = generatePE(sys.argv[1], "Alice", "Bob")

randA = random.randrange(2, q)

maskA = random.randrange(2, q)

scalA = (randA+maskA) % q

elemA = reverse_mult(fast_pow(PW, maskA))

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(('', 6969))
    data, addr = sock.recvfrom(65000)
    scalB = int_from_bytes(data)
    data, addr = sock.recvfrom(65000)
    elemB = int_from_bytes(data)
    sock.sendto(int_to_bytes(scalA), addr)
    sock.sendto(int_to_bytes(elemA), addr)
    secretA = fast_pow(mult(fast_pow(PW, scalB), elemB), randA)
    finalA = hex_to_int(encrypt(str(secretA^elemA^scalA^elemB^scalB)))
    data, addr = sock.recvfrom(65000)
    finalB = int_from_bytes(data)
    sock.sendto(int_to_bytes(finalA), addr)
    if finalA==finalB:
        print("accepted")
    else:
        print("rejected")
