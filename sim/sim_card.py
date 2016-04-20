# LICENSE: GPL2
# (c) 2013 Tom Schouten <tom@getbeep.com>
# (c) 2014, Kamil Wartanowicz <k.wartanowicz@gmail.com>
import logging
from util import hextools
import sim_reader
from util import types
from util import types_g

class SimCard(object):
    def __init__(self, index=0, mode=sim_reader.MODE_PYSCARD, type=types.TYPE_USIM):
        self.simReader = sim_reader.SimReader(mode=mode, type=type)
        self.index = None
        self.mode = mode
        self.imsi = None
        self.atr = None
        self.currentAidId = None # TODO: consider logical channels
        self.currentFile = CurrentFile() # TODO: consider logical channels
        self.routingAttr = RoutingAttr()
        self.swNoError = 0x9000
        self.type = type
        self.activeChannel = 0
        self.logicalChannelClosed = False

    def removeRoutingAttr(self):
        self.routingAttr.insCommon = []
        self.routingAttr.filesCommon = []
        self.routingAttr.filesReplaced = []
        self.routingAttr.insReplaced = []

    def listReaders(self):
        return self.simReader.listReaders()

    def removeAllReaders(self):
        return self.simReader.removeAllReaders()

    def connect(self, index=0):
        self.index = index
        readers = self.simReader.listReaders()
        self.simReader.addReader(index)
        self.simReader.r_createConnection(index)
        self.simReader.c_connect(index)
        self.clearLogicalChannels()
        self.getATR()

    def clearLogicalChannels(self):
        self.logicalChannelClosed = True
        self.activeChannel = 0

    def setActiveChannel(self, channel):
        self.activeChannel = channel

    def getActiveChannel(self):
        return self.activeChannel

    def stop(self):
        self.simReader.close()

    def disconnect(self):
        try:
            self.simReader.c_disconnect(self.index)
        except:
            logging.debug("Reader not connected")
        self.simReader.removeReader(self.index)
        self.atr = None

    def reset(self):
        #TODO: implement different solution, takes too much time on  live SIM
        self.disconnect()
        self.connect(self.index)

    def getATR(self):
        self.atr = self.simReader.c_getATR(self.index)
        self.clearLogicalChannels()
        return self.atr

    def getCachedAtr(self):
        return self.atr

    def setImsi(self, imsi):
        self.imsi = imsi

    def getCurrentAidId(self):
        return self.currentAidId

    def setCurrentAidId(self, aidId):
        self.currentAidId = aidId

    # Perform APDU request on card
    def apdu(self, c_apdu):
        c_apdu = hextools.bytes(c_apdu)
        # Delegate
        try:
            (data,sw1,sw2) = self.simReader.c_transmit(list(c_apdu), self.index)
        except Exception as e:
            #TODO: Remove printing the error. Check why exception is not printed in tes_sat
            logging.error(str(e) + "\n\n")
            raise Exception("Failed to transmit C_APDU: " + hextools.bytes2hex(c_apdu) + "\n" + str(e))
        self.updateSwNoError(sw1, sw2)
        return pack(data,sw1,sw2)

    def updateSwNoError(self, sw1, sw2):
        "cache last success"
        sw = types.packSw(sw1, sw2)
        if sw == types_g.sw.NO_ERROR or sw1 == types_g.sw1.NO_ERROR_PROACTIVE_DATA:
            self.swNoError = sw

    def getCurrentFile(self):
        return self.currentFile

    def getCurrentFilePath(self):
        return self.currentFile.path

    def getCurrentFileType(self):
        return self.currentFile.type

    def getCurrentDirPath(self):
        if types.cmpBitwise(self.currentFile.type, types_g.fileDescriptor.DF_OR_ADF):
            path = self.currentFile.path
        else:
            path = types.parentDirFromPath(self.currentFile.path)
        return path

    def setCurrentFile(self, path, type):
        self.setCurrentFilePath(path)
        self.setCurrentFileType(type)

    def setCurrentFilePath(self, path):
        self.currentFile.path = path

    def setCurrentFileType(self, type):
        self.currentFile.type = type

    def appendCurrentDir(self, name, type=types_g.fileDescriptor.NO_INFORMATION_GIVEN):
        if name == "3F00":
            self.resetCurrentDir()
            return
        if name == "7FFF":
            aidId = self.getCurrentAidId()
            if aidId == None:
                aidId = 0
            self.resetCurrentDir()
            name = "ADF%d" %aidId
            type = types_g.fileDescriptor.DF_OR_ADF
        if not types.cmpBitwise(self.currentFile.type, types_g.fileDescriptor.DF_OR_ADF):
            path = types.parentDirFromPath(self.currentFile.path)
            self.setCurrentFile(path, types_g.fileDescriptor.DF_OR_ADF)
        if types.fidFromPath(self.currentFile.path) == name:
            #parrent directory name must be different than currently selected file
            return
        currentFilePath = self.currentFile.path
        if self.currentFile.path[-1] != "/":
            currentFilePath += "/"
        currentFilePath += name
        self.setCurrentFile(currentFilePath, type)

    def decrementCurrentDir(self):
        if not self.currentFile.path:
            return
        #path = types.parentDirFromPath(self.currentFile.path)
        path = types.parentDirFromPath(self.getCurrentDirPath())
        self.setCurrentFile(path, types_g.fileDescriptor.DF_OR_ADF)

    def resetCurrentDir(self):
        self.setCurrentFile("/", types_g.fileDescriptor.DF_OR_ADF)

FILE_INS = [
    'READ_BINARY',
    'READ_RECORD',
    'SEARCH_RECORD',
    'UPDATE_BINARY',
    'WRITE_BINARY',
    'WRITE_RECORD',
    'UPDATE_RECORD'
    ]

SAT_INS = [
    'TERMINAL_PROFILE',
    'TERMINAL_RESPONSE',
    'FETCH',
    'ENVELOPE',
    ]

FILES_AID = [
    'EF_DIR',
    'A000',
    ]

FILES_REG = [
    'EF_IMSI',
    'EF_LOCI',     #rplmn
    'EF_SMSP',     #sms center number
    'EF_LRPLMNSI', #last RPLMN Selection Indication
    'EF_PLMNSEL',  #plmn selector
    'EF_FPLMN',    #forbiden plmn

    'EF_PSLOCI',
    'EF_EPSLOCI',
    'EF_EPSNSC',
    'EF_LOCIGPRS',

    'EF_KEYS',
    'EF_KEYSPS',
    'EF_KCGPRS',
    'EF_KC',

    'EF_EHPLMN',
    'EF_EHPLMNPI',
    'EF_LRPLMNSI',
    ]

'''
#migth be also considered in FILES_REG
'EF_RPLMN_ACT',
'EF_PLMNWACT',
'EF_HIDDENKEY',
'EF_OPLMNWACT',
'EF_HPLMNWACT',
'RPLMN_ACT',
'''

FILES_REPLACED = []

INS_REPLACED = []

INS_COMMON = [
    'GET_RESPONSE',
    'SELECT_FILE',
    'MANAGE_CHANNEL',
    #'INTERNAL_AUTHENTICATE',
    ]

def pack(reply,sw1,sw2):
    p = list(reply)
    p.append(sw1)
    p.append(sw2)
    return p

class RoutingAttr(object):
    def __init__(self):
        self.insCommon = list(INS_COMMON)
        self.filesCommon = list(FILES_AID)
        self.filesReplaced = list(FILES_REPLACED)
        self.insReplaced = list(INS_REPLACED)

        self.getResponse = None
        self.fileSelected = []
        self.aidToSelect = None
        self.recordEfDirLength = None

    def getFileSelected(self, channel):
        for file in self.fileSelected:
            if not channel or file[1] == channel:
                return file[0]
        return None

    def setFileSelected(self, file, channel):
        for i,fileDict in enumerate(self.fileSelected):
            if fileDict[1] == channel:
                self.fileSelected[i] = (file, channel)
                return
        self.fileSelected.append((file, channel))

class CurrentFile(object):
    def __init__(self):
        self.path = "/"
        self.type = types_g.fileDescriptor.DF_OR_ADF
