#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz <k.wartanowicz@gmail.com>
import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging
import inspect
from optparse import OptionParser
import os
import shlex
import smartcard
from smartcard.Exceptions import CardConnectionException
import subprocess
import threading
import time
import zerorpc
import zmq
from util import hextools

class PyscardRPC(object):
    ####################
    # local methods
    ####################
    def __init__(self, logLevel=logging.WARNING):
        self.setupLogger(logLevel)
        self.readers = []
        self.pollSim = {}

    def setupLogger(self, logLevel):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        consoleHndl = logging.StreamHandler()
        FORMATTER = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt='%H:%M:%S')
        consoleHndl.setFormatter(FORMATTER)
        consoleHndl.setLevel(logLevel)
        logger.addHandler(consoleHndl)

    def runPollSim(self, index):
        if index in self.pollSim.keys():
            # Poll already started.
            return
        pollSim = {index : PollSimThread(self, index)}
        pollSim[index].setDaemon(True)
        pollSim[index].update()
        pollSim[index].start()
        self.pollSim.update(pollSim)

    def stopPollSim(self, index):
        if index not in self.pollSim.keys():
            # Poll not started.
            return
        self.pollSim[index].stop()

    def updatePoll(self, index):
        if index in self.pollSim.keys():
            self.pollSim[index].update()

    # TODO: remove, already implemented in PyscardRpcServerThread.
    # Endpoint is e.g. "tcp://0.0.0.0:4242"
    def runServer(self, endpoint):
        self.s = zerorpc.Server(self)
        #self.s.bind(endpoint)
        try:
            self.s.bind(endpoint)
        except zmq.ZMQError as e:
            if e.errno == zmq.EADDRINUSE:
                logging.info("Pyscard RPC server already running\n")
            else:
                logging.warning("Pyscard RPC server " + endpoint + " could not be started")
            self.s.close()
            sys.exit(0)

        #create result file only when server is started
        dir = os.path.dirname(__file__)
        resultFile = dir + "/../pyscard_rpc.log"
        FORMATTER = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt='%H:%M:%S')
        fileHndl = logging.FileHandler(resultFile, mode='w')
        fileHndl.setFormatter(FORMATTER)
        fileHndl.setLevel(logging.DEBUG)

        logger = logging.getLogger()
        logger.addHandler(fileHndl)

        logging.info("Pyscard RPC Server " + endpoint + " started\n")

        self.s.run()
        return self

    def getReader(self, index):
        for reader in self.readers:
            if reader.index == index:
                return reader
        return None

    def getReaderName(self, index):
        reader = self.getReader(index)
        if not reader:
            return None
        return reader.reader.name

    def getCard(self, index):
        self.checkReader(index)
        return self.getReader(index).card

    def checkReader(self, index):
        if not self.getReader(index):
            raise Exception("Reader with index=%d not created" %index)

    def checkCard(self, index):
        if not self.getCard(index):
            raise Exception("Card for reader with index=%d not created" %index)

    ####################
    # remote methods
    ####################
    def listReaders(self):
        logFunctionAndArgs()
        readers = smartcard.System.readers()
        readersStr = []
        for reader in readers:
            readersStr.append(reader.name)
        logReturnVal(readersStr=readersStr)
        return readersStr

    def addReader(self, index):
        logFunctionAndArgs()
        readersConnected = smartcard.System.readers()
        if not len(readersConnected):
            raise Exception("No reader connected")
        if index >= len(readersConnected):
            raise Exception("Reader id:%d not connected, number of connected readers:%d"
                            %(index, len(readersConnected)))
        newReader = False
        if not self.getReader(index):
            newReader = True
            self.readers.append(Reader())
            self.readers[-1].index = index
            self.readers[-1].reader = readersConnected[index]
        logReturnVal(newReader=newReader)
        return newReader

    def removeReader(self, index):
        logFunctionAndArgs()
        self.checkReader(index)
        for reader in self.readers:
            if reader.index == index:
                del reader
        logReturnVal()
        return None

    def removeAllReaders(self):
        logFunctionAndArgs()
        for reader in self.readers:
            del reader
        logReturnVal()
        return None

    def r_createConnection(self, index):
        logFunctionAndArgs()
        newConnection = False
        self.checkReader(index)
        if not self.getReader(index).card:
            self.getReader(index).card = self.getReader(index).reader.createConnection()
            newConnection = True
        logReturnVal(newConnection=newConnection)
        return newConnection

    def c_connect(self, index):
        logFunctionAndArgs()
        self.checkCard(index)
        self.getCard(index).connect()
        # TODO: get simType from sim_router.
        self.runPollSim(index)
        logReturnVal()
        return None

    def c_disconnect(self, index):
        logFunctionAndArgs()
        self.checkCard(index)
        self.stopPollSim(index)
        self.getCard(index).disconnect()
        logReturnVal()
        return None

    def c_control(self, controlCode, inBuffer, index):
        #logFunctionAndArgs()
        self.checkCard(index)
        self.getCard(index).control(controlCode, inBuffer)
        #logReturnVal()
        return None

    def c_getATR(self, index):
        logFunctionAndArgs()
        self.checkCard(index)
        self.updatePoll(index)
        try:
            atr = self.getCard(index).getATR()
        except CardConnectionException:
            time.sleep(0.1)
            atr = self.getCard(index).getATR()
        logReturnVal(atr=atr)
        return atr

    def c_transmit(self, apdu, index):
        if apdu not in POLL_STATUS_PATTERN_BIN:
            logFunctionAndArgs()
        self.checkCard(index)
        self.updatePoll(index)
        data, sw1, sw2 = self.getCard(index).transmit(apdu)
        if apdu not in POLL_STATUS_PATTERN_BIN:
            logReturnVal(data=data, sw1=sw1, sw2=sw2)
        return data, sw1, sw2

class Reader(object):
    def __init__(self):
        self.index = None
        self.reader = None
        self.card = None

POLL_STATUS_PATTERN_BIN = [
    [0x80, 0xF2, 0x00, 0x0C, 0x00], #3G SIM
    [0xA0, 0xF2, 0x00, 0x00, 0x01], #2G SIM
]

def logFunctionAndArgs():
    frame = inspect.getouterframes(inspect.currentframe())[1][0]
    args, _, _, values = inspect.getargvalues(frame)
    frameinfo = inspect.getframeinfo(frame)
    functionName=inspect.getframeinfo(frame)[2]
    output = ""
    for arg in args[1:]: #[1:] skip the first argument 'self'
        value = values[arg]
        if isinstance(value, str):
            #add apostrophes for string values
            value = "\'"+value+"\'"
        elif isinstance(value, int):
            value = ''.join('%02X' % value)
        else:
            newValue = ""
            for i in value:
                if isinstance(i, int):
                    newValue += '%02X' % i
                else:
                    newValue += str(i)
            value = newValue
        output += arg + '=' + value
        if arg != args[-1]:
            #add comma if not the last element
            output +=','
    #do not print "\n' as a new line
    output = output.replace("\n","\\n")
    logging.info("--> "+functionName+'('+output+')')

def logReturnVal(**kwargs):
    output = ""
    for key, value in kwargs.iteritems():
        if isinstance(value, str):
            #add apostrophes for string values
            value = "\'"+value+"\'"
        elif isinstance(value, int):
            value = ''.join('%02X' % value)
        else:
            newValue = ""
            for i in value:
                if isinstance(i, int):
                    newValue += '%02X' % i
                else:
                    newValue += str(i)
            value = newValue
        output += key + ':' + value + ', '
    output = output.rstrip(', ') #remove last comma and space
    logging.info("<-- "+output+'\n')

######################
#Server configuration#
######################
class PyscardRpcServerThread(threading.Thread):
    def __init__(self, port, logLevel=logging.WARNING):
        threading.Thread.__init__(self)
        self.port = port
        self.logLevel = logLevel
        threading.Thread.setName(self, 'PyscardRpcServerThread')
        self.proc = None
        self.__lock = threading.Lock()

    def run(self):
        self.__lock.acquire();
        #start locally pyscard RPC server
        rpcServerScript = os.path.abspath(__file__).replace("\\", "/")
        scriptCmd = "python %s --port=%d --logLevel=%d" %(rpcServerScript, self.port, self.logLevel)
        self.proc = subprocess.Popen(shlex.split(scriptCmd))
        self.__lock.release();

    def close(self):
        if self.proc:
            subprocess.Popen.terminate(self.proc)

class PollSimThread(threading.Thread):
    def __init__(self, pyscardRpc, index, pollRate=400):
        threading.Thread.__init__(self)
        self.pyscardRpc = pyscardRpc
        self.index = index
        self.pollRate = pollRate
        self.poll = False
        self.startTime = 0
        self.lastUpdate = 0
        self.pattern = 0
        threading.Thread.setName(self, 'PollSimThread')
        self.__lock = threading.Lock()

    def run(self):
        self.__lock.acquire()
        self.poll = True

        while (self.poll):
            self.startTime = time.time()
            if self.startTime - self.lastUpdate > (self.pollRate / 1000.0 - 0.1):
                try:
                    sw1 = self.pyscardRpc.c_transmit(hextools.hex2bytes(POLL_STATUS_PATTERN[self.pattern]),
                                                     self.index)[1]
                    if sw1 != 0x90 and self.pattern < (len(POLL_STATUS_PATTERN) - 1):
                        # Use different pattern e.g. 2G status.
                        self.pattern += 1
                except:
                    logging.error("Stop polling")
                    self.stop()
            self.lastUpdate = time.time()
            time.sleep(self.pollRate / 1000.0)
        self.__lock.release()

    def update(self):
        self.lastUpdate = time.time() - 0.1

    def stop(self):
        self.poll = False
        try:
            self.join()
        except: pass

POLL_STATUS_PATTERN = [
    "80F2000C00", #3G SIM
    "A0F2000001", #2G SIM
    ]

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-p", "--port", dest="port", help="Port number")
    parser.add_option("-v", "--logLevel", dest="logLevel", help="Log level")
    (options, args) = parser.parse_args()
    if options.port:
        try:
            pyscardRpcPort =  int(options.port)
        except:
            raise Exception("Expecting --port argument to be integer, got %r instead" %options.port)
        pyscardRpcPort = options.port
    else:
        pyscardRpcPort = 4148
    if options.logLevel:
        logLevel = int(options.logLevel)
    else:
        logLevel = logging.INFO
    PyscardRPC(logLevel).runServer("tcp://0.0.0.0:"+str(pyscardRpcPort))
