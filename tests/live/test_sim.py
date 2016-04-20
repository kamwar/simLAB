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

MODE_SIM = sim_reader.MODE_PYSCARD

PIN_1 = "1111"
PUK_1 = "11111111"

PIN_1_FALSE = "1112"
PUK_1_FALSE = "11111112"

class TestSim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simCard = sim_card.SimCard(mode=MODE_SIM, type=types.TYPE_USIM)
        cls.simCard.removeAllReaders()
        try:
            cls.simCard.connect(0)
        except Exception as e:
            if "no card in reader" in str(e):
                cls.simCard.stop()
                raise Exception("No card in reader")
        cls.simRouter = sim_router.SimRouter(cards=[cls.simCard], type=types.TYPE_USIM, mode=sim_router.SIMTRACE_OFFLINE)
        cls.simRouter.run(mode=sim_router.ROUTER_MODE_DISABLED)
        cls.simCtrl = cls.simRouter.simCtrl
        cls.sendApdu = cls.simRouter.simCtrl.sendApdu

    def test_1_getAtr(self):
        atr = self.simCard.getATR()
        logging.info("ATR: %s" %hextools.bytes2hex(atr))
        self.assertGreater(len(atr), 4)

    def test_2_select_file(self):
        #SELECT_AID
        self.simCtrl.selectAid()
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("00A40004023F00")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        self.assertGreater(sw2, 2)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)

        #SELECT_FILE EF_ICCID
        sw1, sw2, data = self.sendApdu("00A40004022FE2")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #SELECT_FILE EF_ICCID by path from MF
        sw1, sw2, data = self.sendApdu("00A40804022FE2")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #SELECT_FILE EF_IMSI by path from MF
        sw1, sw2, data = self.sendApdu("00A40804047FFF6F07")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

    def test_3_enable_pin(self):
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(attemptsLeft, "PUK needed")

        if enabled:
            #disable pin
            sw1, sw2, data = self.sendApdu("0026000108%sFFFFFFFF" %PIN_1.encode("hex"))
            types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertFalse(enabled)
        self.assertTrue(attemptsLeft, "No attempts left. PUK needed")

        #enable pin
        sw1, sw2, data = self.sendApdu("0028000108%sFFFFFFFF" %PIN_1.encode("hex"))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)
        self.assertTrue(attemptsLeft, "No attempts left. PUK needed")

    @unittest.skip("It's risky to block PIN1 on live SIM")
    def test_4_unblock_pin(self):
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)
        self.assertTrue(attemptsLeft, "No attempts left. PUK needed")

        #VERIFY
        sw1, sw2, data = self.sendApdu("0020000108%sFFFFFFFF" %PIN_1.encode("hex"))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)

        #block PIN
        for i in range(attemptsLeft):
            sw1, sw2, data = self.sendApdu("0020000108%sFFFFFFFF" %PIN_1_FALSE.encode("hex"))
            _attemptsLeft = attemptsLeft - i - 1
            types.assertSw(sw1, sw2, checkSw1='CODE_ATTEMPTS_LEFT', raiseException=True)
            left = self.simCtrl.pin1Status()
            self.assertEqual(left, _attemptsLeft)

        #unblock PIN
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertFalse(attemptsLeft, "PIN is not blocked")

        attemptsLeft = self.simCtrl.pin1UnblockStatus()
        self.assertTrue(attemptsLeft>=10, "PUK1 attempts left: %d" %attemptsLeft)
        sw1, sw2, data = self.sendApdu("002C000110%s%sFFFFFFFF" %(PUK_1.encode("hex"), PIN_1.encode("hex")))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

    def test_5_read_imsi(self):
        enabled = self.simCtrl.pin1Enabled()
        attemptsLeft = self.simCtrl.pin1Status()
        self.assertTrue(enabled)
        self.assertTrue(attemptsLeft, "PUK needed")

        self.simCtrl.selectAid()
        #SELECT_FILE IMSI
        sw1, sw2, data = self.sendApdu("00A40004026F07")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #READ BINARY
        tagData = types.parseFcpTlv(data, types.FILE_LENGTH_EXCLUDING_SI_TAG)
        if tagData == None:
           raise Exception("BINARY_LENGTH_TAG not found in FCI")
        imsiLength = tagData[1]
        sw1, sw2, data = self.sendApdu("00B00000%02X" %imsiLength)
        if types_g.sw[(sw1<<8) + sw2] == 'SECURITY_STATUS_NOT_SATISFIED':
            #VERIFY
            sw1, sw2, data = self.sendApdu("0020000108%sFFFFFFFF" %PIN_1.encode("hex"))
            types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
            #repeat READ BINARY
            sw1, sw2, data = self.sendApdu("00B00000%02X" %imsiLength)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        imsi = hextools.decode_BCD(data)[3:]
        logging.info("IMSI: %s" %imsi)

    def test_6_manage_channel(self):
        originChannel = 0

        """ Open first free channel """
        # MANAGE CHANNEL: OPEN (first free)
        sw1, sw2, data = self.sendApdu("0%01X7000%02X01" %(originChannel, 0))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        targetChannel = data[0] # 2
        # MANAGE CHANNEL: CLOSE
        sw1, sw2, data = self.sendApdu("0%01X7080%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        """ Select on not open channel (when targetChannel = 0) """
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("0%01XA40004023F00" %targetChannel)
        # Two possible responses
        if types.assertSw(sw1, sw2, checkSw1='WRONG_INSTRUCTION_CLASS', raiseException=False):
            types.assertSw(sw1, sw2, checkSw='LOGICAL_CHANNEL_NOT_SUPPORTED', raiseException=True)

        """ Open, Select and Close channel """
        # MANAGE CHANNEL: OPEN (chosen)
        sw1, sw2, data = self.sendApdu("0%01X7000%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        #SELECT_AID (ADF_USIM)
        # Select some AID (applet) on a specific channel.
        aid = self.simCtrl.getAid()
        apdu = "0%01XA40404%02X%s" %(targetChannel, len(aid)/2, aid)
        sw1, sw2, data = self.sendApdu(apdu)
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("0%01XA40004023F00" %targetChannel)
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        self.assertGreater(sw2, 2)
        # MANAGE CHANNEL: CLOSE
        sw1, sw2, data = self.sendApdu("0%01X7080%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        """ Open first free channel (when targetChannel = 0) """
        # MANAGE CHANNEL: OPEN (first free)
        sw1, sw2, data = self.sendApdu("0%01X7000%02X01" %(originChannel, 0))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        self.assertEqual(data[0], targetChannel)

        originChannel = data[0] # 1
        # MANAGE CHANNEL: OPEN (non-basic origin channel)
        sw1, sw2, data = self.sendApdu("0%01X7000%02X01" %(originChannel, 0))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        self.assertEqual(data[0], originChannel + 1)
        targetChannel = data[0] # 2

        """ Select MF on Non-Basic channel """
        #SELECT_AID (ADF_USIM)
        apdu = "0%01XA40404%02X%s" %(targetChannel, len(aid)/2, aid)
        sw1, sw2, data = self.sendApdu(apdu)
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("0%01XA40004023F00" %targetChannel)
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        self.assertGreater(sw2, 2)
        """ Close Non-Basic channel """
        # MANAGE CHANNEL: CLOSE
        sw1, sw2, data = self.sendApdu("0%01X7080%02X00" %(originChannel, targetChannel))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)

        """ Select IMSI file on Basic channel """
        #SELECT_AID (ADF_USIM)
        #self.simCtrl.selectAid()
        apdu = "00A40404%02X%s" %(len(aid)/2, aid)
        sw1, sw2, data = self.sendApdu(apdu)
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        #SELECT_FILE IMSI
        sw1, sw2, data = self.sendApdu("00A40004026F07")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', raiseException=True)
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        tagData = types.parseFcpTlv(data, types.FILE_LENGTH_EXCLUDING_SI_TAG)
        if tagData == None:
           raise Exception("BINARY_LENGTH_TAG not found in FCI")
        imsiLength = tagData[1]

        """ Read IMSI file on Basic channel """
        #READ BINARY
        sw1, sw2, data = self.sendApdu("00B00000%02X" %imsiLength)
        if types_g.sw[(sw1<<8) + sw2] == 'SECURITY_STATUS_NOT_SATISFIED':
            #VERIFY
            sw1, sw2, data = self.sendApdu("0020000108%sFFFFFFFF" %PIN_1.encode("hex"))
            types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
            #repeat READ BINARY
            sw1, sw2, data = self.sendApdu("00B00000%02X" %imsiLength)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR', raiseException=True)
        imsi = hextools.decode_BCD(data)[3:]
        logging.info("IMSI: %s" %imsi)

    def tearDown(self):
        self.simCard.reset()

    @classmethod
    def tearDownClass(cls):
        cls.simCard.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()