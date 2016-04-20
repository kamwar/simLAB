#!/usr/bin/python
# LICENSE: GPL2
# (c) 2016 Janusz Kuszczynski

import unittest
import logging
import os
import shlex
import signal
import subprocess
import threading
import time
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from util import types

DBUS_ENABLE = True
if os.name != 'posix':
    DBUS_ENABLE = False
if DBUS_ENABLE:
    import dbus


@unittest.skipUnless(DBUS_ENABLE, "Windows doesn't support DBUS")
class TestDBus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = SimlabServerThread()
        cls.server.setDaemon(True)
        cls.server.start()
        time.sleep(1)
        cls.bus = dbus.SessionBus()
        cls.session = cls.bus.get_object("org.sim.simlab", "/org/sim/simlab")
        cls.interface = dbus.Interface(cls.session, "org.sim.simlab")

    def test_1_pwd(self):
        result = self.interface.pwd()
        self.assertStatus(result)

    def test_2_long_command(self):
        self.interface.cd('/')
        result = self.interface.ls()
        self.assertStatus(result)

    def test_3_get_plmn(self):
        result = self.interface.get_plmn()
        self.assertStatus(result)

    def assertStatus(self, status):
        if 'status OK' in status:
            logging.info('Test OK')
        else:
            logging.warning("".join(status))
            self.fail(status)

    @classmethod
    def tearDownClass(cls):
        cls.server.close()

class SimlabServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        threading.Thread.setName(self, 'SimlabServerThread')
        self.proc = None
        self.__lock = threading.Lock()

    def run(self):
        self.__lock.acquire()
        # Can't run plac in thread thus script is loaded from external script
        scriptPath = os.path.abspath(os.path.dirname(__file__))
        scriptPath = os.path.join(scriptPath, "../../mim/mim_tmp.py").replace("\\", "/")
        scriptFile = open(scriptPath, "w")
        scriptFile.write(script)
        scriptFile.close()
        scriptCmd = "python " + scriptPath
        self.proc = subprocess.Popen(shlex.split(scriptCmd))
        self.__lock.release()

    def close(self):
        types.killProcess("mim_tmp.py")

script = '''
import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging
from sim import sim_router
from sim import sim_card
from sim import sim_reader
from util import types
logging.basicConfig(level=logging.INFO, format='%(message)s')
simType=types.TYPE_USIM
simCard = sim_card.SimCard(mode=sim_reader.MODE_SIM_SOFT, type=simType)
simCard.removeAllReaders()
simCard.connect(sim_reader.READER_ID_0)
simRouter = sim_router.SimRouter(cards=[simCard],
                       atr=None,
                       type=simType,
                       mode=sim_router.SIMTRACE_OFFLINE)
simRouter.run(mode=sim_router.ROUTER_MODE_DBUS)
'''

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()

