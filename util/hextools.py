# LICENSE: GPL2
# (c) 2013 Tom Schouten <tom@getbeep.com>

import array

def bytes2hex(bytes, separator=""):
    hexStr = "".join(map(lambda v: "%02X%s"%(v, separator), bytes))
    if hexStr and hexStr[-1] == separator:
        #remove unwanted char at the end
        hexStr = hexStr[0:-1]
    return hexStr

def hex2bytes(hex):
    return map(ord,hex.decode("hex"))

def bytes2string(bytes):
    return array.array('B',bytes).tostring()

def bytes(x):
    if type(x) == str:
        x = hex2bytes(x)
    return x

def hex(x):
    if type(x) == str:
        return x
    if type(x) == int:
        return be_int_bytes(x)
    if type(x) == list:
        return bytes2hex(x)
    if type(x) == tuple:
        return bytes2hex(list(x))
    if type(x) == bytearray:
        return bytes2hex(x)
    raise Exception(x)

def string(x):
    return bytes2string(bytes(x))

def le_int_bytes(i):
    lst = []
    while (i != 0):
        lst.append(i & 0xFF)
        i = i >> 8
    return lst
def be_int_bytes(i):
    lst = le_int_bytes(i)
    lst.reverse()
    return lst

# Remove spaces
def strip(str):
    return str.replace(" ", "")


class chunks:
    def __init__(self, lst, nb):
        self.lst = lst
        self.nb = nb
    def __iter__(self):
        return self
    def next(self):
        if not len(self.lst):
            raise StopIteration
        rv = self.lst[0:self.nb]
        self.lst = self.lst[self.nb:]
        return rv

# see iso7816_slave.h
# AT91 is little endian.
def le_u32(val):
    return [val & 0xFF,
            (val >> 8) & 0xFF,
            (val >> 16) & 0xFF,
            (val >> 24) & 0xFF];
def u32(val):
    return le_u32(val)

def be_u16(val):
    return [(val >> 8) & 0xFF, val & 0xFF]


# big endian byte list to integer
def le_int(lst):
    shift = 0
    acc = 0
    for b in lst:
        acc += b << shift
        shift += 8
    return acc

def be_int(lst):
    r_lst = list(lst)
    r_lst.reverse()
    return le_int(r_lst)

def all_FF(msg):
    for b in msg:
        if b != 0xFF:
            return False
    return True

def pathstring(path):
    return "".join(map((lambda p: "/%s" % hex(p)), path))


def decode_BCD(data=[]):
    string = ''
    for B in data:
        string += "%01X" %(B & 0x0F)
        hidig = B >> 4
        if (hidig < 10):
            string += str( hidig )
    return string

def encode_BCD(data=[]):
    data = map(lambda x: int(x, 16), data)
    acc = []
    while len(data):
        head = data[0:2]
        data = data[2:]
        if (len(head) == 1):
            head.append(0xF)
        byte = head[0] + 0x10 * head[1]
        acc.append(byte)
    return acc

def test():
    assert "00010203" == hex([0,1,2,3])
    assert "ABCD" == hex("ABCD")
    assert [0x7F, 0] == hex(0x7F00)
    assert 0x00010203 == be_int([0,1,2,3])
    assert 0x03020100 == le_int([0,1,2,3])
    assert "/A/B" == pathstring(["A","B"])

    assert [0x21,0x43] == encode_BCD("1234")
    assert "1234"      == decode_BCD([0x21,0x43])
    assert [0x21,0xF3] == encode_BCD("123")
    assert "123"       == decode_BCD([0x21,0xF3])

    assert [[1,2],[3,4]] == [x for x in chunks([1,2,3,4], 2)]

    logging.info("hextools: OK")




if __name__ == '__main__':
    test()
