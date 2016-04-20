#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Mikolaj Bartnicki
# (c) 2015 Kamil Wartanowicz
import logging
"""
USIM authentication algorithm.
Names of Dummy XOR variables

Variable | bits  | name
======================================
key      |  128  |  Key Value (K)
rand        128     Random Value (RAND)
amf      |  16   |  AMF
sqn      |  48   |  SQN

ak       |  48   |  AK
mac      |  64   |  MAC
autn     |  128  |  AUTN

res      | 32-128| RES (XDOUT RES)
ck       |  128  |  CK
ik       |  128  |  IK
kc       |  128  |  KC
"""

# masks used to cut lengths of values
MASK_48_BIT = 0xFFFFFFFFFFFF
MASK_64_BIT = 0xFFFFFFFFFFFFFFFF
MASK_128_BIT = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

AUTH_RESULT_OK = 0xDB
AUTH_RESULT_SYNCHORNISATION_FAILURE = 0xDC

def rotateLeft128bit(i, n):
    """Rotate left i by n bytes.
    The result value lenght is set to 128 bits."""
    mask = (i >> (128 - n)) & MASK_128_BIT
    i = ((i << n) | mask) & MASK_128_BIT
    return i

def dummyXor(key, rand, sqn, amf, autn):
    """Perform a Dummy XOR authentication algorithm."""
    #http://cosconor.fr/GSM/Divers/Others/Cours/SIM%20Cards/GemXplore3G%20V2.pdf
    xdout = key ^ rand
    ck = rotateLeft128bit(xdout, 8)
    ik = rotateLeft128bit(xdout, 16)
    ak = (xdout >> 56) & MASK_48_BIT

    if autn:
        sqnFromAutn = (autn >> 80) ^ ak
        if sqnFromAutn != sqn:
            #TODO: implement sqn range check and EF_SQN update
            logging.info("Received sqn: %s, expected: %s" %(keyHex(sqnFromAutn), keyHex(sqn)))
            sqn = sqnFromAutn
    cdout = (sqn << 16) | amf
    xmac = (xdout >> 64) ^ cdout
    outAutn = ((sqn ^ ak) << 80) | (amf << 64) | xmac
    kc = (ik & MASK_64_BIT) ^ (ik >> 64) ^ (ck & MASK_64_BIT) ^ (ck >> 64)
    return {'res': xdout, 'autn' : outAutn, 'ck': ck, 'ik': ik, 'kc' : kc}

def dummyXorHex(key, rand, sqn, amf, autn):
    key = int(key, 16)
    rand = int(rand, 16)
    sqn = int(sqn, 16)
    amf = int(amf, 16)
    if autn:
        autn = int(autn, 16)
    result = dummyXor(key, rand, sqn, amf, autn)
    for key in result:
        if key != 'kc':
            result[key] = keyHex(result[key])
        else:
            result[key] = keyHex(result[key], length=8)
    return result

def keyHex(key, length=16):
    length = 2 * length
    data = "%02X" %(key)
    currentlength = len(data)
    if currentlength < length:
        data = "%s%s" %("0" * (length-currentlength), data)
    return data

def dummyXorData(rand, key, sqn, amf, autn=None):
    result = dummyXorHex(key, rand, sqn, amf, autn)
    if result['autn'] != autn:
        return []
    data = "%02X" %AUTH_RESULT_OK
    data += "%02X%s" %(len(result['res'])/2, result['res'])
    data += "%02X%s" %(len(result['ck'])/2, result['ck'])
    data += "%02X%s" %(len(result['ik'])/2, result['ik'])
    #service 27 available in EF_UST
    data += "%02X%s" %(len(result['kc'])/2, result['kc'])
    return data

def authenticateDummyXor(rand, key, sqn, amf, autn=None):
    return dummyXorData(rand, key, sqn, amf, autn)