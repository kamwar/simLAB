#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz

import inspect
import logging
import os
import sys
import traceback

import sim_xml
import sim_soft
import sat_ctrl

from util import types_g
from util import types

class SoftCard(object):
    def __init__(self, simType=types.TYPE_USIM, file=None):
        self.simType = simType
        if not file:
            file = os.path.dirname(__file__) + "/sim_backup.xml"
        self.file = file

    def connect(self):
        self.init()

    def init(self):
        #TODO: check if already opened, then close might be needed
        self.simXml = sim_xml.SimXml(self.file)
        self.satCtrl = sat_ctrl.SatCtrl(types.TYPE_SIM, self.simXml)
        self.simHandler = sim_soft.SimHandler(self.simXml, self.satCtrl, self.simType)

    def getATR(self):
        self.init()
        return self.simXml.getAtr()

    def transmit(self, apdu):
        try:
            return self._transmit(apdu)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stackTrace = "".join(traceback.format_tb(exc_traceback))
            error = exc_value
            raise Exception("%s\nError: %s" %(stackTrace, error))

    def _transmit(self, apdu):
        sw = 0x9000
        data = []

        channel = types.channel(apdu)
        if channel > types.MAX_LOGICAL_CHANNELS - 1:
            sw = types_g.sw.CLASS_NOT_SUPPORTED
            return data, sw

        # Check if the channel is open
        if self.simHandler.isChannelOpen(channel) == False:
            sw = types_g.sw.LOGICAL_CHANNEL_NOT_SUPPORTED
            return data, sw
        # TODO: open channel through SELECT command
        self.simHandler.setChannel(channel)

        ins = types.insName(apdu)
        if ins == "SELECT_FILE":
            data, sw = self.simHandler.select(apdu)
        elif ins == "GET_RESPONSE":
            data, sw = self.simHandler.getResponse(apdu)
        elif ins == "READ_BINARY":
            data, sw = self.simHandler.readBinary(apdu)
        elif ins == "VERIFY_PIN":
            data, sw = self.simHandler.verifyPin(apdu)
        elif ins == "UNBLOCK_PIN":
            data, sw = self.simHandler.unblockPin(apdu)
        elif ins == "CHANGE_PIN":
            data, sw = self.simHandler.changePin(apdu)
        elif ins == "ENABLE_PIN":
            data, sw = self.simHandler.enablePin(apdu)
        elif ins == "DISABLE_PIN":
            data, sw = self.simHandler.disablePin(apdu)
        elif ins == "STATUS":
            data, sw = self.simHandler.status(apdu)
        elif ins == "SEARCH_RECORD":
            data, sw = self.simHandler.searchRecord(apdu)
        elif ins == "READ_RECORD":
            data, sw = self.simHandler.readRecord(apdu)
        elif ins == "UPDATE_BINARY":
            data, sw = self.simHandler.updateBinary(apdu)
        elif ins == "UPDATE_RECORD":
            data, sw = self.simHandler.updateRecord(apdu)
        elif ins == "DEACTIVATE_FILE":
            data, sw = self.simHandler.deactivateFile(apdu)
        elif ins == "ACTIVATE_FILE":
            data, sw = self.simHandler.activateFile(apdu)
        elif ins == "TERMINAL_PROFILE":
            data, sw = self.satCtrl.terminalProfile(apdu)
        elif ins == "TERMINAL_RESPONSE":
            data, sw = self.satCtrl.terminalResponse(apdu)
        elif ins == "FETCH":
            data, sw = self.satCtrl.fetch(apdu)
        elif ins == "ENVELOPE":
            data, sw = self.satCtrl.envelope(apdu)
        elif ins == "MANAGE_CHANNEL":
            data, sw = self.simHandler.manageChannel(apdu)
        elif ins == 'INTERNAL_AUTHENTICATE':
            data, sw = self.simHandler.authenticate(apdu)
        elif ins == "CREATE_FILE":
            data, sw = self.simHandler.createFile(apdu)
        elif ins == "DELETE_FILE":
            data, sw = self.simHandler.deleteFile(apdu)
        elif ins == "RESIZE_FILE":
            data, sw = self.simHandler.resizeFile(apdu)
        elif ins == 'DE':
            data, sw = self.simHandler.unknownInstruction()
        else:
            raise Exception("Invalid instruction: %s" %ins)

        return data, sw

class SoftReader(object):
    def __init__(self, name):
        self.name = name
        self.card = None

    def createConnection(self, type=types.TYPE_SIM):
        self.card = SoftCard(simType=type)
        return self.card

reader1 = SoftReader('Soft SIM reader 0')
reader2 = SoftReader('Soft SIM reader 1')

READERS = [reader1, reader2]

class Reader(object):
    def __init__(self):
        self.index = None
        self.reader = None
        self.card = None

class SimSoftCtrl(object):
    def __init__(self, type=types.TYPE_USIM, logLevel=logging.INFO):
        dir = os.path.dirname(__file__)
        resultFile = dir + "/../sim_soft.log"
        FORMATTER = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt='%H:%M:%S')
        fileHndl = logging.FileHandler(resultFile, mode='w')
        fileHndl.setFormatter(FORMATTER)
        fileHndl.setLevel(logLevel)
        logger = logging.getLogger("sim_soft")
        #dont't propagate to root logger
        logger.propagate=False
        logger.handlers = []
        logger.setLevel(logLevel)
        logger.addHandler(fileHndl)
        self.logging = logger
        self.readers = []
        self.simType = type

    def close(self):
        pass

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

    #exported methods
    def listReaders(self):
        self.logFunctionAndArgs()
        readers = READERS
        readersStr = []
        for reader in readers:
            readersStr.append(reader.name)
        self.logReturnVal(readersStr=readersStr)
        return readersStr

    def addReader(self, index):
        self.logFunctionAndArgs()
        self.readers.append(Reader())
        readersConnected = READERS
        if not len(readersConnected):
            raise Exception("No reader connected")
        if index >= len(readersConnected):
            raise Exception("Reader id:%d not connected, number of connected readers:%d"
                            %(index, len(readersConnected)))
        self.readers[-1].index = index
        self.readers[-1].reader = readersConnected[index]
        self.logReturnVal()
        return None

    def removeReader(self, index):
        self.logFunctionAndArgs()
        self.checkReader(index)
        for reader in self.readers:
            if reader.index == index:
                del reader
        self.logReturnVal()
        return None

    def removeAllReaders(self):
        self.logFunctionAndArgs()
        for reader in self.readers:
            del reader
        self.logReturnVal()
        return None

    def r_createConnection(self, index):
        self.logFunctionAndArgs()
        self.checkReader(index)
        self.getReader(index).card = self.getReader(index).reader.createConnection(type=self.simType)
        return None

    def c_connect(self, index):
        self.logFunctionAndArgs()
        self.checkCard(index)
        self.getCard(index).connect()
        self.logReturnVal()
        return None

    def c_disconnect(self, index):
        self.logFunctionAndArgs()
        self.checkCard(index)
        self.getCard(index).disconnect()
        self.logReturnVal()
        return None

    def c_getATR(self, index):
        self.logFunctionAndArgs()
        self.checkCard(index)
        atr = self.getCard(index).getATR()
        self.logReturnVal(atr=atr)
        return atr

    def c_transmit(self, apdu, index):
        self.logFunctionAndArgs()
        self.checkCard(index)
        data, sw = self.getCard(index).transmit(apdu)
        sw1 = sw>>8
        sw2 = sw & 0x00FF
        self.logReturnVal(data=data, sw1=sw1, sw2=sw2)
        return data, sw1, sw2

    def logFunctionAndArgs(self):
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
        self.logging.info("--> "+functionName+'('+output+')')

    def logReturnVal(self, **kwargs):
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
        self.logging.info("<-- "+output+'\n')
