#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from sim import sim_router
from sim import sim_card
from util import hextools
from util import types_g
from util import types
import unittest
import logging

from sim import sim_reader
from sim import sim_ctrl_2g
from sim import sim_ctrl_3g

MODE_SIM = sim_reader.MODE_SIM_SOFT
SIM_TYPE = types.TYPE_SIM

PIN_1 = "1111"
PUK_1 = "11111111"

PIN_1_FALSE = "1112"
PUK_1_FALSE = "11111112"

class TestSim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simCard = sim_card.SimCard(mode=MODE_SIM, type=SIM_TYPE)
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
        cls.sendApdu = cls.simCtrl.sendApdu

    def test_1_getAtr(self):
        atr = self.simCard.getATR()
        logging.info("ATR: %s" %hextools.bytes2hex(atr))
        self.assertGreater(len(atr), 4)

    def test_2_select_file(self):
        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.sendApdu("A0A40000027F20")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("A0A40000023F00")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        self.assertGreater(sw2, 2)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)

        #SELECT_FILE EF_ICCID
        sw1, sw2, data = self.sendApdu("A0A40000022FE2")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

    def test_3_enable_pin(self):
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(attemptsLeft, "PUK needed")

        if enabled:
            #disable pin
            sw1, sw2, data = self.sendApdu("A026000108%sFFFFFFFF" %PIN_1.encode("hex"))
            types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertFalse(enabled)
        self.assertTrue(attemptsLeft, "No attempts left. PUK needed")

        #enable pin
        sw1, sw2, data = self.sendApdu("A028000108%sFFFFFFFF" %PIN_1.encode("hex"))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)
        self.assertTrue(attemptsLeft, "No attempts left. PUK needed")

    def test_4_unblock_pin(self):
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)
        self.assertTrue(attemptsLeft, "No attempts left. PUK needed")

        #VERIFY
        sw1, sw2, data = self.sendApdu("A020000108%sFFFFFFFF" %PIN_1.encode("hex"))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)

        #block PIN
        for i in range(attemptsLeft):
            sw1, sw2, data = self.sendApdu("A020000108%sFFFFFFFF" %PIN_1_FALSE.encode("hex"))

            _attemptsLeft = attemptsLeft - i - 1
            if _attemptsLeft:
                types.assertSw(sw1, sw2, checkSw='GSM_ACCESS_CONDITION_NOT_FULFILLED', raiseException=True)
            else:
                types.assertSw(sw1, sw2, checkSw='GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION', raiseException=True)
            left = self.simCtrl.pin1Status()
            self.assertEqual(left, _attemptsLeft)

        #unblock PIN
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertFalse(attemptsLeft, "PIN is not blocked")

        attemptsLeft = self.simCtrl.pin1UnblockStatus()
        self.assertTrue(attemptsLeft, "SIM is permanently blocked")

        for i in range(attemptsLeft - 2):
            sw1, sw2, data = self.sendApdu("A02C000010%s%sFFFFFFFF" %(PUK_1_FALSE.encode("hex"), PIN_1.encode("hex")))

            _attemptsLeft = attemptsLeft - i - 1
            if _attemptsLeft:
                types.assertSw(sw1, sw2, checkSw='GSM_ACCESS_CONDITION_NOT_FULFILLED', raiseException=True)
            else:
                types.assertSw(sw1, sw2, checkSw='GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION', raiseException=True)
            left = self.simCtrl.pin1UnblockStatus()
            self.assertEqual(left, _attemptsLeft)

        attemptsLeft = self.simCtrl.pin1UnblockStatus()
        self.assertGreater(attemptsLeft, 1, "Prevent permanent blocking of SIM")

        sw1, sw2, data = self.sendApdu("A02C000010%s%sFFFFFFFF" %(PUK_1.encode("hex"), PIN_1.encode("hex")))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

    def test_5_read_imsi(self):
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)
        self.assertTrue(attemptsLeft, "PUK needed")

        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.sendApdu("A0A40000027F20")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #SELECT_FILE IMSI
        sw1, sw2, data = self.sendApdu("A0A40000026F07")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #READ BINARY
        length = data[3]
        sw1, sw2, data = self.sendApdu("A0B00000%02X" %length)
        if types_g.sw[(sw1<<8) + sw2] == 'GSM_ACCESS_CONDITION_NOT_FULFILLED':
            #VERIFY
            sw1, sw2, data = self.sendApdu("A020000108%sFFFFFFFF" %PIN_1.encode("hex"))
            types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
            #repeat READ BINARY
            sw1, sw2, data = self.sendApdu("A0B00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        imsi = hextools.decode_BCD(data)[3:]
        logging.info("IMSI: %s" %imsi)

    @unittest.skip("Might be not supported on 2G SIM")
    def test_6_manage_channel(self):
        originChannel = 0
        targetChannel = 2

        """ Select on not open channel """
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("A%01XA40000023F00" %targetChannel)
        types.assertSw(sw1, sw2, checkSw='LOGICAL_CHANNEL_NOT_SUPPORTED', raiseException=True)

        """ Open, Select and Close channel """
        # MANAGE CHANNEL: OPEN (chosen)
        sw1, sw2, data = self.sendApdu("A%01X7000%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("A%01XA40000023F00" %targetChannel)
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        self.assertGreater(sw2, 2)
        # MANAGE CHANNEL: CLOSE
        sw1, sw2, data = self.sendApdu("A%01X7080%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        """ Open first free channel (when targetChannel = 0) """
        # MANAGE CHANNEL: OPEN (first free)
        sw1, sw2, data = self.sendApdu("A%01X7000%02X01" %(originChannel, 0))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        self.assertEqual(data[0], 1)

        originChannel = data[0] # 1
        # MANAGE CHANNEL: OPEN (non-basic origin channel)
        sw1, sw2, data = self.sendApdu("A%01X7000%02X01" %(originChannel, 0))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        self.assertEqual(data[0], originChannel + 1)
        targetChannel = data[0] # 2

        """ Select IMSI file on Basic channel """
        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.sendApdu("A0A40000027F20")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        #SELECT_FILE IMSI
        sw1, sw2, data = self.sendApdu("A0A40000026F07")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        imsiLen = data[3]
        """ Select MF on Non-Basic channel """
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("A%01XA40000023F00" %targetChannel)
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', raiseException=True)
        self.assertGreater(sw2, 2)
        """ Read IMSI file on Basic channel """
        #READ BINARY
        sw1, sw2, data = self.sendApdu("A0B00000%02X" %imsiLen)
        if types_g.sw[(sw1<<8) + sw2] == 'GSM_ACCESS_CONDITION_NOT_FULFILLED':
            #VERIFY
            sw1, sw2, data = self.sendApdu("A020000108%sFFFFFFFF" %PIN_1.encode("hex"))
            types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
            #repeat READ BINARY
            sw1, sw2, data = self.sendApdu("A0B00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        imsi = hextools.decode_BCD(data)[3:]
        logging.info("IMSI: %s" %imsi)

        """ Close Non-Basic channel """
        # MANAGE CHANNEL: CLOSE
        sw1, sw2, data = self.sendApdu("A%01X7080%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

    def tearDown(self):
        self.simCard.reset()

    @classmethod
    def tearDownClass(cls):
        cls.simCard.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()