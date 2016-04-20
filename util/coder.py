#!/usr/bin/python
# -*- coding: utf8

import logging

GSM7_BASIC = (u"@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>"
              u"?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM7_EXT = (u"````````````````````^```````````````````{}`````\\````````````[~]`"
            u"|````````````````````````````````````€``````````````````````````")

def encodeGsm7(plaintext):
    res = ""
    f = -1
    t = 0
    bytes = getBytes(plaintext)
    bytesLength = len(bytes)
    for b in bytes:
        f = f+1
        t = (f%8)+1
        res += getEncode(b, t, t-1, f, f+1, 8-t, bytesLength, bytes)
    return res

def decodeGsm7(codedtext):
    if not codedtext:
        raise Exception("Empy data to decode")
    hexparts = chunks(codedtext, 2)
    number   = 0
    bitcount = 0
    output   = ''
    found_external = False
    for byte in hexparts:
        byte = int(byte, 16);
        # add data on to the end
        number = number + (byte << bitcount)
        # increase the counter
        bitcount = bitcount + 1
        # output the first 7 bits
        if number % 128 == 27:
             '''skip'''
             found_external = True
        else:
            if found_external == True:
                 character = GSM7_EXT[number % 128]
                 found_external = False
            else:
                 character = GSM7_BASIC[number % 128]
            output = output + character

        # then throw them away
        number = number >> 7
        # every 7th letter you have an extra one in the buffer
        if bitcount == 7:
            if number % 128 == 27:
                '''skip'''
                found_external = True
            else:
                if found_external == True:
                    character = GSM7_EXT[number % 128]
                    found_external = False
                else:
                    character = GSM7_BASIC[number % 128]
                output = output + character

            bitcount = 0
            number = 0
    return output

def getEncode(currentByte, index, bitRightCount, position, nextPosition, leftShiftCount, bytesLength, bytes):
    if index < 8:
        byte = currentByte >> bitRightCount
        if nextPosition < bytesLength:
            idx2 = bytes[nextPosition]
            byte = byte | ((idx2) << leftShiftCount)
            byte = byte & 0x000000FF
        else:
            byte = byte & 0x000000FF
        return chr(byte).encode('hex').upper()
    return ''

def getBytes(plaintext):
    if type(plaintext) != str:
         plaintext = str(plaintext)
    bytes = []
    for c in plaintext.decode('utf-8'):
        idx = GSM7_BASIC.find(c)
        if idx != -1:
            bytes.append(idx)
        else:
            idx = GSM7_EXT.find(c)
            if idx != -1:
                bytes.append(27)
                bytes.append(idx)
    return bytes

def chunks(l, n):
    if n < 1:
        n = 1
    return [l[i:i + n] for i in range(0, len(l), n)]
