#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz
# (c) 2014 Szymon Mielczarek

import sys
import os.path
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from sim import sim_router
from sim import sim_card
from util import types
import unittest
import logging

from sim import sim_reader

MODE_SIM = sim_reader.MODE_SIM_SOFT

PIN_1 = "1111"
PUK_1 = "11111111"

PIN_1_FALSE = "1112"
PUK_1_FALSE = "11111112"

class TestSimRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simCard = sim_card.SimCard(mode=MODE_SIM, type=types.TYPE_SIM)
        cls.simCard.removeAllReaders()
        try:
            cls.simCard.connect(0)
        except Exception as e:
            if "no card in reader" in str(e):
                cls.simCard.stop()
                raise Exception("No card in reader")
        cls.simRouter = sim_router.SimRouter(cards=[cls.simCard], type=types.TYPE_SIM, mode=sim_router.SIMTRACE_OFFLINE)
        cls.simRouter.run(mode=sim_router.ROUTER_MODE_DISABLED)
        cls.simCtrl = cls.simRouter.simCtrl
        cls.sendApdu = cls.simRouter.simCtrl.sendApdu

    def test_1_create_setUpMenu(self):
        # create Set Up Menu
        sw1, sw2, data = self.sendApdu(
            "A01000001FFFFFFFFF7F0F00DF7F03071FE2080C0003000E000000000000000000000000")
        types.assertSw(sw1, sw2, checkSw1='NO_ERROR_PROACTIVE_DATA', raiseException=True)
        self.assertGreater(sw2, 2)

    def test_2_select_menu_item1(self):
        # envelope: MENU_SELECTION - Item1
        item = 0
        sw1, sw2, data = self.sendApdu("A0C2000009D3078202018190018" + str(item))
        types.assertSw(sw1, sw2, checkSw1='NO_ERROR_PROACTIVE_DATA', raiseException=True)
        length = sw2
        # fetch: provideLocalInformation(local_info.IMEI_OF_THE_TERMINAL)
        sw1, sw2, data = self.sendApdu("A0120000%02X" %length)
        # send terminal response with IMEI: 00440245243851-2
        sw1, sw2, data = self.sendApdu(
            "A01400001681030226010202828103010014080A40044225345801")

    def test_3_select_menu_item2(self):
        # envelope: MENU_SELECTION - Item2
        item = 1
        sw1, sw2, data = self.sendApdu("A0C2000009D3078202018190018" + str(item))
        types.assertSw(sw1, sw2, checkSw1='NO_ERROR_PROACTIVE_DATA', raiseException=True)
        length = sw2
        # fetch: GET_INPUT
        sw1, sw2, data = self.sendApdu("A0120000%02X" %length)
        # terminal response: input text
        sw1, sw2, data = self.sendApdu(
            "A0140000148103052301020282818301008D06043030313031")
        time.sleep(2)

    def test_4_select_menu_item3(self):
        # envelope: MENU_SELECTION - Item3
        item = 2
        sw1, sw2, data = self.sendApdu("A0C2000009D3078202018190018" + str(item))
        types.assertSw(sw1, sw2, checkSw1='NO_ERROR_PROACTIVE_DATA', raiseException=True)
        length = sw2
        # fetch - PLAY_TONE
        sw1, sw2, data = self.sendApdu("A0120000%02X" %length)
        # terminal response
        sw1, sw2, data = self.sendApdu(
            "A01400000C810304200002028281830100")

    def test_5_select_menu_item4(self):
        # envelope: MENU_SELECTION - Item4
        item = 3
        sw1, sw2, data = self.sendApdu("A0C2000009D3078202018190018" + str(item))
        types.assertSw(sw1, sw2, checkSw1='NO_ERROR_PROACTIVE_DATA', raiseException=True)
        length = sw2
        # fetch
        sw1, sw2, data = self.sendApdu("A0120000%02X" % length)

        # envelope: SELECT_ITEM - Item 1
        # terminal response
        sw1, sw2, data = self.sendApdu("A01400000F810302240002028281830100900180")

    def test_6_select_menu_item5(self):
        # envelope: MENU_SELECTION - Item5
        item = 4
        sw1, sw2, data = self.sendApdu("A0C2000009D3078202018190018" + str(item))
        types.assertSw(sw1, sw2, checkSw1='NO_ERROR_PROACTIVE_DATA', raiseException=True)
        length = sw2
        # fetch
        sw1, sw2, data = self.sendApdu("A0120000%02X" %length)

    @classmethod
    def tearDownClass(cls):
        time.sleep(1)
        cls.simCard.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()