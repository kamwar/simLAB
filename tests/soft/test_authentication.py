#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Kamil Wartanowicz
# (c) 2015 Mikolaj Bartnicki

import sys
import os.path
import logging
import unittest
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from sim_soft import sim_auth

class TestAuthentication(unittest.TestCase):
    def test_1_dummy_xor(self):
        # input:
        key = "00112233445566778899AABBCCDDEEFF"
        rand = "31323131353836343132313135383634"
        sqn = "000000000000"
        amf = "0000"

        # expected output
        res = "31231302716D5043B9AB9B8AF9E5D8CB"
        ck = "231302716D5043B9AB9B8AF9E5D8CB31"
        ik = "1302716D5043B9AB9B8AF9E5D8CB3123"
        kc = "0000000000000000"
        autn = "02716D5043B9000031231302716D5043"

        logging.info("Codes to check:\n"
                     "key=%s\n"
                     "rand=%s\n"
                     "sqn=%s\n"
                     "amf=%s\n"
                        %(key, rand, sqn, amf))
        result = sim_auth.dummyXorHex(key, rand, sqn, amf, None)

        self.assertEqual(result['res'], res)
        self.assertEqual(result['ck'], ck)
        self.assertEqual(result['ik'], ik)
        self.assertEqual(result['kc'], kc)
        self.assertEqual(result['autn'], autn)

    def test_2_dummy_xor(self):
        # input:
        key = "00112233445566778899AABBCCDDEEFF"
        rand = "41ec50d284b5284fb9a317e9f089f247"
        sqn = "FFFFFFFFFFFF"
        amf = "8000"

        # expected output
        autn = "1E3F1FB1C7CE8000BE028D1E3F1FCE38"
        res = "41FD72E1C0E04E38313ABD523C541CB8"
        ck = "FD72E1C0E04E38313ABD523C541CB841"
        ik = "72E1C0E04E38313ABD523C541CB841FD"
        kc = "087C4F48E6D2F0B7"

        logging.info("Codes to check:\n"
                     "key=%s\n"
                     "rand=%s\n"
                     "sqn=%s\n"
                     "amf=%s\n"
                        %(key, rand, sqn, amf))
        result = sim_auth.dummyXorHex(key, rand, sqn, amf, None)

        self.assertEqual(result['res'], res)
        self.assertEqual(result['ck'], ck)
        self.assertEqual(result['ik'], ik)
        self.assertEqual(result['kc'], kc)
        self.assertEqual(result['autn'], autn)

    def test_3_dummy_xor_data(self):
        # input:
        key = "00112233445566778899AABBCCDDEEFF"
        rand = "0123456789ABCDEF0123456789ABCDEF"
        sqn = "000000000000"
        amf = "0000"
        autn = "54CDFEAB9889000001326754CDFEAB98"

        logging.info("Codes to check:\n"
                     "key=%s\n"
                     "rand=%s\n"
                     "sqn=%s\n"
                     "amf=%s\n"
                        %(key, rand, sqn, amf))

        result = sim_auth.dummyXorData(key, rand, sqn, amf, autn)
        self.assertEqual(result,
                         "DB"                                 #OK
                         "1001326754CDFEAB9889BAEFDC45762310" #RES
                         "10326754CDFEAB9889BAEFDC4576231001" #CK
                         "106754CDFEAB9889BAEFDC457623100132" #IK
                         "080000000000000000")                #KC

    def test_4_dummy_xor_data(self):
        '''TODO: implement sqn range check'''
        #apdu 00880081221041EC50D284B5284FB9A317E9F089F24710E1C0E04E3822800041FD72E1C0F3CE38
        # input:
        key = "00112233445566778899AABBCCDDEEFF"
        rand = "41ec50d284b5284fb9a317e9f089f247"
        sqn = "000000000000"
        amf = "8000"
        autn = "1E3F1FB1C7CE8000BE028D1E3F1FCE38"

        logging.info("Codes to check:\n"
                     "key=%s\n"
                     "rand=%s\n"
                     "sqn=%s\n"
                     "amf=%s\n"
                        %(key, rand, sqn, amf))

        result = sim_auth.dummyXorData(key, rand, sqn, amf, autn)
        self.assertEqual(result,
                         "DB"                                 #OK
                         "1041FD72E1C0E04E38313ABD523C541CB8" #RES
                         "10FD72E1C0E04E38313ABD523C541CB841" #CK
                         "1072E1C0E04E38313ABD523C541CB841FD" #IK
                         "08087C4F48E6D2F0B7")                #KC

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()