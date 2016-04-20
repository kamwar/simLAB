# LICENSE: GPL2
# (c) 2013 Tom Schouten <tom@getbeep.com>

import socket
import struct

# log APDUs to gsmtap
# http://wiki.wireshark.org/GSMTAP
# http://bb.osmocom.org/trac/wiki/GSMTAP

### to test: setup wireshark to listen on "lo"
# from util import gsmtap
# gsmtap.loghex("A0A40000023f00", "9000")


gsmtap_hdr = [2, # GSMTAP_VERSION,
              4, # nb of u32 in header
              4, # GSMTAP_TYPE_SIM,
              0,0,0,0,0,0,0,0,0,0,0,0,0]

# gsmtap_addr = ("127.0.0.1", 4729)
gsmtap_addr = ("<broadcast>", 4729)
gsmtap_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
gsmtap_sock.bind(('127.0.0.1', 0))
# broadcast avoids ICMP port unreachable
gsmtap_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


def bytes2str(bytes):
    return struct.pack('B'*len(bytes), *bytes)
def hex2bytes(hex):
    return map(ord,hex.decode("hex"))

# input = bytes
def log(c_apdu, r_apdu=[]):
    msg = list(gsmtap_hdr) + list(c_apdu) + list(r_apdu)
    gsmtap_sock.sendto(bytes2str(msg), gsmtap_addr)

# input = hex string
def loghex(c, r=""):
    log(hex2bytes(c), hex2bytes(r))
