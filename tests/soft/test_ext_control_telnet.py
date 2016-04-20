#!/usr/bin/python
# LICENSE: GPL2
# (c) 2016 Kamil Wartanowicz
import unittest
import logging
import os
import re
import shlex
import signal
import subprocess
import sys
import telnetlib
import threading
import time
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from util import types

HOST = "localhost"
prompt = "i> "


class TestTelnet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = SimlabServerThread()
        cls.server.setDaemon(True)
        cls.server.start()
        time.sleep(3)
        cls.telnet = TelnetSimlab()
        cls.simLab = cls.telnet.send

    def test_1_pwd(self):
        status, data = self.simLab("pwd")
        self.assertTrue(status)
        logging.info(data)
        self.assertTrue(data)

    def test_2_long_command(self):
        self.simLab("cd ADF0")
        status, data = self.simLab("ls")
        self.assertTrue(status)
        logging.info(data)
        self.assertTrue(data)

    @classmethod
    def tearDownClass(cls):
        cls.telnet.close()
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

class TelnetSimlab(object):
    def __init__(self, port=2199):
        self.tn = telnetlib.Telnet(HOST, port)
        # Read prompt
        self.tn.read_until(prompt, timeout=1)

    def clearReadBuffer(self):
        # Clear buffer
        self.tn.read_very_eager()

    def send(self, cmd):
        self.clearReadBuffer()
        self.tn.write(cmd + "\r\n")
        return self.getResponse()

    def validateResponse(self, out):
        if len(out.split("\n")) > 2:
            raise Exception("Response data not expected: " + out)

    def statusOk(self, out):
        self.validateResponse(out)
        statusRe = re.search("status (.*)", out)
        if not statusRe:
            raise Exception("Status data not expected: " + out)
        status = statusRe.group(1)
        if status == "OK":
            return True
        else:
            return False

    def getData(self, out):
        self.validateResponse(out)
        dataRe = re.search("data (.*)", out)
        if not dataRe:
            return None
        data = dataRe.group(1)
        return data

    def getResponse(self):
        out = self.tn.read_until(prompt, timeout=30)
        out = out.rstrip(prompt)
        out = out.replace("\r", "")
        out = out.rstrip("\n")
        status = self.statusOk(out)
        data = self.getData(out)
        return status, data

    def close(self):
        self.tn.close()

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
simRouter.run(mode=sim_router.ROUTER_MODE_TELNET)
'''

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()
