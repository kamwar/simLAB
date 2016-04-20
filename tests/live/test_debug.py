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
import time

from sim import sim_reader
from sim import sim_ctrl_2g
from sim import sim_ctrl_3g
from sim import sim_shell

MODE_SIM = sim_reader.MODE_PYSCARD
SIM_TYPE = types.TYPE_USIM

PIN_1 = "1111"
PUK_1 = "11111111"

PIN_1_FALSE = "1112"
PUK_1_FALSE = "11111112"

class TestDebug(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim1 = sim_card.SimCard()
        cls.sim1.removeAllReaders()
        cls.sim1.connect(0)
        cls.sim2 = sim_card.SimCard(mode=sim_reader.MODE_SIM_SOFT, type=SIM_TYPE)
        try:
            cls.sim2.connect(0)
        except Exception as e:
            if "no card in reader" in str(e):
                cls.sim2.stop()
                raise Exception("No card in reader")
        cls.simRouter = sim_router.SimRouter(cards=[cls.sim1, cls.sim2], type=types.TYPE_USIM, mode=sim_router.SIMTRACE_OFFLINE)
        cls.simRouter.run(mode=sim_router.ROUTER_MODE_DISABLED)
        #update soft SIM for SAT handling
        cls.simRouter.getMainCard(1).routingAttr.insReplaced = sim_card.SAT_INS
        cls.sendApdu = cls.simRouter.simCtrl.sendApdu
        cls.shell = cls.simRouter.shell

    def test_1_send_apdu(self):
        #self.simCtrl.selectAid()
        sw1, sw2, data = self.sendApdu("801000001EFFFFFFFF7F9F00DFFF00001FE2000000C3"
                                       "FB000700016800710000000018",
                                       mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("8012000076", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("801400000C810301250002028281830100",
                                       mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("80C2000009D30782020181900181",
                                       mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("8012000026", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("80140000108103022300020282818301008D020430",
                                       mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("801200002A", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("80140000148103022300020282818301008D060430303"
                                       "13031", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("801200001F", mode=sim_router.INJECT_WITH_FORWARD)
        #wait for post action finish in sat_ctrl
        time.sleep(3)

    def test_2_send_apdu(self):
        #self.simCtrl.selectAid()
        sw1, sw2, data = self.sendApdu("801000001EFFFFFFFF7F9F00DFFF00001FE2000000C3FB"
                                       "000700016800710000000018",
                                       mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("8012000076", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("80C2000009D30782020181900185",
                                       mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("801200000B", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("8014000017810305260002028281030106130962F060002"
                                       "093E00022", mode=sim_router.INJECT_WITH_FORWARD)
        sw1, sw2, data = self.sendApdu("8014000017810305260002028281030106130962F0600020"
                                       "93E00022", mode=sim_router.INJECT_WITH_FORWARD)
        #wait for post action finish in sat_ctrl
        time.sleep(3)
        #uncomment when fixed
        #self.shell.cd(".")

    @classmethod
    def tearDownClass(cls):
        cls.sim1.stop()
        cls.sim2.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()
