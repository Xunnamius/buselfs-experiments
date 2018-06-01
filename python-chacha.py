#!/usr/bin/env python3

# This script generates hashes for the experiment, timing it and reporting on the
# results

import os
import sys
import gc
import time
import subprocess
import serial
import pysodium
from vendor.pyWattsup import WattsUp
from cryptography.hazmat.primitives.ciphers import (Cipher, algorithms, modes)
from cryptography.hazmat.backends import default_backend

TRIALS = 3
INNER_TRIALS = 50
BUFFER_FLUSH_SLEEP = 1

################################################################################

if len(sys.argv) != 2:
    print('Usage: {} <coretype>'.format(sys.argv[0]))
    sys.exit(1)

coreType = sys.argv[1]
trials = TRIALS

RANDOM = {
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
    def newfn():
        for retval in retvals:
            yield retval
    return newfn

def do_trial(description, out, fn):
    print('waiting for write buffer flush...')
    time.sleep(BUFFER_FLUSH_SLEEP)

    print(description)
    print(description, file=out)

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
    ciphertext = encryptor.update(RANDOM[data]) + encryptor.finalize()

    return (ciphertext, nonce, key)

def chacha20_encrypt(data):
    nonce = os.urandom(8)
    key = os.urandom(32)
    return (pysodium.crypto_stream_chacha20_xor(RANDOM[data], nonce, key), nonce, key)

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
    ciphertext = encryptor.update(RANDOM[data]) + encryptor.finalize()

    return (ciphertext, nonce, key, encryptor.tag)

def chacha20_poly1305_encrypt(data):
    nonce = os.urandom(8)
    key = os.urandom(32)
    return (pysodium.crypto_aead_chacha20poly1305_encrypt(RANDOM[data], '', nonce, key), nonce, key)

def aes_cbc_encrypt(data):
    key = os.urandom(32)
    aes = algorithms.AES(key)
    nonce = os.urandom(int(aes.block_size / 8))

    # Construct an AES-GCM Cipher object with the given key and a
    # randomly generated IV.
    encryptor = Cipher(
        aes,
        modes.CBC(nonce),
        backend=default_backend()
    ).encryptor()

    # Encrypt the plaintext and get the associated ciphertext.
    # GCM does not require padding.
    ciphertext = encryptor.update(RANDOM[data]) + encryptor.finalize()

    return (ciphertext, nonce, key)

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

# Accepts generators as arguments, not bits
def aes_cbc_decrypt(data, nonce, key):
    # Construct an AES-CBC Cipher object with the given key and a
    # randomly generated IV.
    decryptor = Cipher(
        algorithms.AES(next(key)),
        modes.CBC(next(nonce)),
        backend=default_backend()
    ).decryptor()

    return decryptor.update(next(data)) + decryptor.finalize()

with open('/home/odroid/bd3/rsync/energy-AES-1/results/shmoo.{}.results'.format(coreType), 'a+') as out:
    while trials:
        trials = trials - 1
        trial = TRIALS-trials

        # acdata1, acnonce1, ackey1  = do_trial('beginning trial {}-1-1E of {} (small.random, AES-CTR encrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_encrypt, 'small'))
        # cc20data1, cc20nonce1, cc20key1 = do_trial('beginning trial {}-1-2E of {} (small.random, ChaCha20 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_encrypt, 'small'))
        # agdata1, agnonce1, agkey1, agtag1  = do_trial('beginning trial {}-1-3E of {} (small.random, AES-GCM encrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_encrypt, 'small'))
        # ccpdata1, ccpnonce1, ccpkey1 = do_trial('beginning trial {}-1-4E of {} (small.random, ChaCha20-Poly1305 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_encrypt, 'small'))
        
        acdata2, acnonce2, ackey2 = do_trial('beginning trial {}-2-1E of {} (large.random, AES-CTR encrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_encrypt, 'large'))
        do_trial('beginning trial {}-2-1D of {} (large.random, AES-CTR decrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_decrypt, acdata2(), acnonce2(), ackey2()))
        del acdata2, acnonce2, ackey2 # Hopefully this helps curb the exponential growth of memory usage...
        gc.collect()

        cc20data2, cc20nonce2, cc20key2 = do_trial('beginning trial {}-2-2E of {} (large.random, ChaCha20 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_encrypt, 'large'))
        do_trial('beginning trial {}-2-2D of {} (large.random, ChaCha20 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_decrypt, cc20data2(), cc20nonce2(), cc20key2()))
        del cc20data2, cc20nonce2, cc20key2
        gc.collect()

        agdata2, agnonce2, agkey2, agtag2  = do_trial('beginning trial {}-2-3E of {} (large.random, AES-GCM encrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_encrypt, 'large'))
        do_trial('beginning trial {}-2-3D of {} (large.random, AES-GCM decrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_decrypt, agdata2(), agnonce2(), agkey2(), agtag2()))
        del agdata2, agnonce2, agkey2, agtag2
        gc.collect()

        ccpdata2, ccpnonce2, ccpkey2 = do_trial('beginning trial {}-2-4E of {} (large.random, ChaCha20-Poly1305 encrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_encrypt, 'large'))
        do_trial('beginning trial {}-2-4D of {} (large.random, ChaCha20-Poly1305 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_decrypt, ccpdata2(), ccpnonce2(), ccpkey2()))
        del ccpdata2, ccpnonce2, ccpkey2
        gc.collect()

        acbcdata2, acbcnonce2, acbckey2 = do_trial('beginning trial {}-2-5E of {} (large.random, AES-CBC encrypt)'.format(trial, TRIALS), out, make_lambda(aes_cbc_encrypt, 'large'))
        do_trial('beginning trial {}-2-5D of {} (large.random, AES-CBC decrypt)'.format(trial, TRIALS), out, make_lambda(aes_cbc_decrypt, acbcdata2(), acbcnonce2(), acbckey2()))
        del acbcdata2, acbcnonce2, acbckey2
        gc.collect()

        # do_trial('beginning trial {}-1-1D of {} (small.random, AES-CTR decrypt)'.format(trial, TRIALS), out, make_lambda(aes_ctr_decrypt, acdata1(), acnonce1(), ackey1()))
        # do_trial('beginning trial {}-1-2D of {} (small.random, ChaCha20 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_decrypt, cc20data1(), cc20nonce1(), cc20key1()))
        # do_trial('beginning trial {}-1-3D of {} (small.random, AES-GCM decrypt)'.format(trial, TRIALS), out, make_lambda(aes_gcm_decrypt, agdata1(), agnonce1(), agkey1(), agtag1()))
        # do_trial('beginning trial {}-1-4D of {} (small.random, ChaCha20-Poly1305 decrypt)'.format(trial, TRIALS), out, make_lambda(chacha20_poly1305_decrypt, ccpdata1(), ccpnonce1(), ccpkey1()))
        
        print('trial {}/{} complete for this configuration'.format(trial, TRIALS))

wattsup.serial.close()
print('~~done~~')
exit(0)
