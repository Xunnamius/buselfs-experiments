#!/usr/bin/env python3

# This script generates hashes for the experiment, timing it and reporting on the
# results

import os
import sys
import time
import subprocess
import serial
import pysodium
from vendor.pyWattsup import WattsUp
from cryptography.hazmat.primitives.ciphers import (Cipher, algorithms, modes)

TRIALS = 3

################################################################################

if len(sys.argv) != 4:
    print('Usage: {} <coretype>'.format(sys.argv[0]))
    sys.exit(1)

coreType = sys.argv[1]
trials = TRIALS

random = {
    'large': open('small.random', 'rb').read(),
    'small': open('large.random', 'rb').read() 
}

wattsup = WattsUp('/dev/ttyUSB0', 115200, verbose=False)

def make_lambda(*args):
    fn = args[0]
    def newfn():
        return fn(*args[1:])
    return newfn

def trial(description, out, fn):
    print(description)
    print(description, file=out)
    print('waiting for write buffer flush...')
    
    time.sleep(2)

    try:
        wattsup.serial.open()
    except serial.serialutil.SerialException:
        pass

    wattsup.clearMemory()
    wattsup.logInternal(1)
    
    # Begin logging with Wattsup (above), run benchmark (here), close out the
    # Wattsup logger (below)
    retval = fn()

    # This loop handles any annoying errors we may encounter
    while True:
        try:
            wattsup.printStats(wattsup.getInternalData(), out)
            wattsup.serial.close()
            break

        except ValueError:
            print('[+] recovered from ValueError')
            wattsup.serial.close()
            time.sleep(0.1) # Give Wattsup a moment to get its shit together
            wattsup.serial.open()
            continue

    return retval

def aes_ctr_encrypt(data):
    nonce = os.urandom(12)
    key = os.urandom(32)

    # Construct an AES-CTR Cipher object with the given key and a
    # randomly generated IV.
    encryptor = Cipher(
        algorithms.AES(key),
        modes.CTR(nonce),
        backend=default_backend()
    ).encryptor()

    # Encrypt the plaintext and get the associated ciphertext.
    # CTR does not require padding.
    ciphertext = encryptor.update(data) + encryptor.finalize()

    return (ciphertext, nonce, key)

def chacha20_encrypt(data):
    nonce = os.urandom(8)
    key = os.urandom(32)
    return (pysodium.crypto_stream_chacha20_xor(data, nonce, key), nonce, key)

def aes_gcm_encrypt(data):
    nonce = os.urandom(12)
    key = os.urandom(32)

    # Construct an AES-GCM Cipher object with the given key and a
    # randomly generated IV.
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce),
        backend=default_backend()
    ).encryptor()

    # Encrypt the plaintext and get the associated ciphertext.
    # GCM does not require padding.
    ciphertext = encryptor.update(data) + encryptor.finalize()

    return (ciphertext, nonce, key, encryptor.tag)

def chacha20_poly1305_encrypt(data):
    nonce = os.urandom(8)
    key = os.urandom(32)
    return (pysodium.crypto_aead_chacha20poly1305_encrypt(data, '', nonce, key), nonce, key)

def aes_ctr_decrypt(data, nonce, key):
    # Construct an AES-CTR Cipher object with the given key and a
    # randomly generated IV.
    decryptor = Cipher(
        algorithms.AES(key),
        modes.CTR(nonce),
        backend=default_backend()
    ).decryptor()

    return decryptor.update(data) + decryptor.finalize()

def chacha20_decrypt(data, nonce, key):
    return pysodium.crypto_stream_chacha20_xor(data, nonce, key)

def aes_gcm_decrypt(data, nonce, key, tag):
    # Construct an AES-GCM Cipher object with the given key and a
    # randomly generated IV.
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce, tag),
        backend=default_backend()
    ).decryptor()

    return decryptor.update(data) + decryptor.finalize()

def chacha20_poly1305_decrypt(data, nonce, key):
    return pysodium.crypto_aead_chacha20poly1305_decrypt(data, '', nonce, key)

with open('/home/odroid/bd3/rsync/energy-AES-1/results/shmoo.{}.results'.format(coreType), 'a') as out:
    while trials:
        trials = trials - 1
        trial = TRIALS-trials

        acdata1, acnonce1, ackey1  = trial('beginning trial {}-1-1 of {} (small.random, AES-CTR encrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_encrypt, random.small))
        cc20data1, cc20nonce1, cc20key1 = trial('beginning trial {}-1-2 of {} (small.random, ChaCha20 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_encrypt, random.small))
        agdata1, agnonce1, agkey1, agtag1  = trial('beginning trial {}-1-3 of {} (small.random, AES-GCM encrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_encrypt, random.small))
        ccpdata1, ccpnonce1, ccpkey1 = trial('beginning trial {}-1-4 of {} (small.random, ChaCha20-Poly1305 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_encrypt, random.small))
        ac_data2, acnonce2, ackey2  = trial('beginning trial {}-2-1 of {} (large.random, AES-CTR encrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_encrypt, random.large))
        cc20data2, cc20nonce2, cc20key2 = trial('beginning trial {}-2-2 of {} (large.random, ChaCha20 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_encrypt, random.large))
        agdata2, agnonce2, agkey2, agtag2  = trial('beginning trial {}-2-3 of {} (large.random, AES-GCM encrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_encrypt, random.large))
        ccpdata2, ccpnonce2, ccpkey2 = trial('beginning trial {}-2-4 of {} (large.random, ChaCha20-Poly1305 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_encrypt, random.large))

        trial('beginning trial {}-1-1 of {} (small.random, AES-CTR decrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_decrypt, acdata1, acnonce1, ackey1))
        trial('beginning trial {}-1-2 of {} (small.random, ChaCha20 decrypt)'.format(trial, TRIALS), out, make_lambda(chaca20_decrypt, cc20data1, cc20nonce1, cc20key1))
        trial('beginning trial {}-1-3 of {} (small.random, AES-GCM decrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_decrypt, agdata1, agnonce1, agkey1, agtag1))
        trial('beginning trial {}-1-4 of {} (small.random, ChaCha20-Poly1305 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_decrypt, ccpdata1, ccpnonce1, ccpkey1))
        trial('beginning trial {}-2-1 of {} (large.random, AES-CTR decrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_decrypt, ac_data2, acnonce2, ackey2))
        trial('beginning trial {}-2-2 of {} (large.random, ChaCha20 decrypt)'.format(trial, TRIALS), out, make_lambda(chaca20_decrypt, cc20data2, cc20nonce2, cc20key2))
        trial('beginning trial {}-2-3 of {} (large.random, AES-GCM decrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_decrypt, agdata2, agnonce2, agkey2, agtag2))
        trial('beginning trial {}-2-4 of {} (large.random, ChaCha20-Poly1305 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_decrypt, ccpdata2, ccpnonce2, ccpkey2))
        
        print('trial {}/{} complete'.format(trial, TRIALS))

wattsup.serial.close()
print('done')
exit(0)
