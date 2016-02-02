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
from cryptography.hazmat.backends import default_backend

TRIALS = 3
INNER_TRIALS = 10

################################################################################

if len(sys.argv) != 4:
    print('Usage: {} <coretype>'.format(sys.argv[0]))
    sys.exit(1)

coreType = sys.argv[1]
trials = TRIALS

random = {
    'large': open('large.random', 'rb').read(),
    'small': open('small.random', 'rb').read()
}

wattsup = WattsUp('/dev/ttyUSB0', 115200, verbose=False)

def make_lambda(*args):
    fn = args[0]
    def newfn():
        return fn(*args[1:])
    return newfn

def make_generator(retvals):
    for retval in retvals:
        yield retval

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
    inner_trials = INNER_TRIALS
    retvals = []
    makeGenerators = False

    while inner_trials:
        inner_trials = inner_trials - 1
        inner_retvals = fn()

        # It is assumed that inner_retvals's structure will NOT change during
        # the trial or else this code will not work!
        if isinstance(inner_retvals, tuple):
            makeGenerators = True
            diff = len(retvals) - len(inner_retvals)

            if diff != 0:
                for i in range(abs(diff)):
                    retvals.append([])

            for index in range(len(inner_retvals)):
                retvals[index].append(inner_retvals[index])
        else:
            if makeGenerators:
                raise RuntimeError('makeGenerators assertion failed')
            retvals.append(inner_retvals)

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

    if makeGenerators:
        generators = []

        for collection in retvals:
            generators.append(make_generator(collection))

        retvals = generators

    return retvals

def aes_ctr_encrypt(data):
    key = os.urandom(32)
    aes = algorithms.AES(key)
    nonce = os.urandom(int(aes.block_size / 8))

    # Construct an AES-CTR Cipher object with the given key and a
    # randomly generated IV.
    encryptor = Cipher(
        aes,
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

# Accepts generators as arguments, not bits
def aes_ctr_decrypt(data, nonce, key):
    # Construct an AES-CTR Cipher object with the given key and a
    # randomly generated IV.
    decryptor = Cipher(
        algorithms.AES(next(key)),
        modes.CTR(next(nonce)),
        backend=default_backend()
    ).decryptor()

    return decryptor.update(next(data)) + decryptor.finalize()

# Accepts generators as arguments, not bits
def chacha20_decrypt(data, nonce, key):
    return pysodium.crypto_stream_chacha20_xor(next(data), next(nonce), next(key))

# Accepts generators as arguments, not bits
def aes_gcm_decrypt(data, nonce, key, tag):
    # Construct an AES-GCM Cipher object with the given key and a
    # randomly generated IV.
    decryptor = Cipher(
        algorithms.AES(next(key)),
        modes.GCM(next(nonce), next(tag)),
        backend=default_backend()
    ).decryptor()

    return decryptor.update(next(data)) + decryptor.finalize()

# Accepts generators as arguments, not bits
def chacha20_poly1305_decrypt(data, nonce, key):
    return pysodium.crypto_aead_chacha20poly1305_decrypt(next(data), '', next(nonce), next(key))

with open('/home/odroid/bd3/rsync/energy-AES-1/results/shmoo.{}.results'.format(coreType), 'a') as out:
    while trials:
        trials = trials - 1
        trial = TRIALS-trials

        acdata1, acnonce1, ackey1  = trial('beginning trial {}-1-1 of {} (small.random, AES-CTR encrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_encrypt, random['small']))
        cc20data1, cc20nonce1, cc20key1 = trial('beginning trial {}-1-2 of {} (small.random, ChaCha20 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_encrypt, random['small']))
        agdata1, agnonce1, agkey1, agtag1  = trial('beginning trial {}-1-3 of {} (small.random, AES-GCM encrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_encrypt, random['small']))
        ccpdata1, ccpnonce1, ccpkey1 = trial('beginning trial {}-1-4 of {} (small.random, ChaCha20-Poly1305 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_encrypt, random['small']))
        ac_data2, acnonce2, ackey2  = trial('beginning trial {}-2-1 of {} (large.random, AES-CTR encrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_encrypt, random['large']))
        cc20data2, cc20nonce2, cc20key2 = trial('beginning trial {}-2-2 of {} (large.random, ChaCha20 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_encrypt, random['large']))
        agdata2, agnonce2, agkey2, agtag2  = trial('beginning trial {}-2-3 of {} (large.random, AES-GCM encrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_encrypt, random['large']))
        ccpdata2, ccpnonce2, ccpkey2 = trial('beginning trial {}-2-4 of {} (large.random, ChaCha20-Poly1305 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_encrypt, random['large']))

        trial('beginning trial {}-1-1 of {} (small.random, AES-CTR decrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_decrypt, acdata1(), acnonce1(), ackey1()))
        trial('beginning trial {}-1-2 of {} (small.random, ChaCha20 decrypt)'.format(trial, TRIALS), out, make_lambda(chaca20_decrypt, cc20data1(), cc20nonce1(), cc20key1()))
        trial('beginning trial {}-1-3 of {} (small.random, AES-GCM decrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_decrypt, agdata1(), agnonce1(), agkey1(), agtag1()))
        trial('beginning trial {}-1-4 of {} (small.random, ChaCha20-Poly1305 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_decrypt, ccpdata1(), ccpnonce1(), ccpkey1()))
        trial('beginning trial {}-2-1 of {} (large.random, AES-CTR decrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_decrypt, ac_data2(), acnonce2(), ackey2()))
        trial('beginning trial {}-2-2 of {} (large.random, ChaCha20 decrypt)'.format(trial, TRIALS), out, make_lambda(chaca20_decrypt, cc20data2(), cc20nonce2(), cc20key2()))
        trial('beginning trial {}-2-3 of {} (large.random, AES-GCM decrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_decrypt, agdata2(), agnonce2(), agkey2(),agtag2()))
        trial('beginning trial {}-2-4 of {} (large.random, ChaCha20-Poly1305 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_decrypt, ccpdata2(), ccpnonce2(), ccpkey2()))
        
        print('trial {}/{} complete'.format(trial, TRIALS))

wattsup.serial.close()
print('done')
exit(0)
