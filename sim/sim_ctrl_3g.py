#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz
import logging

from util import hextools
from util import types_g
from util import types
import sim_codes
import sim_router
from sim import file_parser
from sim import sim_files

SIM_ID_0 = 0
SIM_ID_ALL = 0xFF

logicalChannel = 0
INIT_CONTROL_CHANNEL = True


class SimCtrl(object):
    def __init__(self, router):
        self.router = router
        global logicalChannel
        self.logicalChannel = logicalChannel
        self.file_parser = file_parser.FileParser()
        self.simFiles = sim_files.SimFiles(self.router.simType)
        self.setSrvCtrlId(0)

    def init(self):
        if INIT_CONTROL_CHANNEL:
            self.initLogicalChannels()
        self.simFiles.resolveAdfs(self.readFileData('/2F00'))
        # Select default applet (ADF_USIM)
        self.selectAid(aidId=0)
        self.selectMf()

    def initLogicalChannels(self):
        if self.logicalChannel:
            if self.verifyChannel(self.logicalChannel):
                return
            logging.info("Reinitialize logical channel, current channel: %d" %self.logicalChannel)
        channel = None
        nbrOfCards = self.router.getNbrOfCards()
        simIdChannelOpened = []

        for simId in range(nbrOfCards):
            self.setSrvCtrlId(simId)
            #assign free logical channel
            channelTmp = self.openChannel(0, 0)
            if not channelTmp:
                logging.error("Failed to init logical channel for simId:%d" %simId)
                channel = None
                break

            simIdChannelOpened.append(simId)

            if channel and channel != channelTmp:
                logging.warning("Assigned logicalChannel:%d, expecting:%d" %(channelTmp, channel))
                channel = None
                break

            #Check if logical channel supports PIN verify. If not consider logical channel as
            #not supporting all features and close it
            if not self.verifyChannel(channelTmp):
                logging.info("Close deafult logical channel %d" %channelTmp)
                channel = None
                break
            channel = channelTmp

        if channel:
            self.setLogicalChannel(channel)
        else:
            self.setLogicalChannel(channel=0)
            #close opened logical channels
            for simId in simIdChannelOpened:
                self.setSrvCtrlId(simId)
                self.closeChannel(0, channelTmp)
        self.setSrvCtrlId(0)

    def verifyChannel(self, channel):
        sw1 = self.sendApdu("%02X20000100" %channel)[0]
        if sw1 != types_g.sw1.CODE_ATTEMPTS_LEFT:
            return False
        return True

    def setLogicalChannel(self, channel):
        global logicalChannel
        logicalChannel = channel
        self.logicalChannel = channel
        self.setActiveChannel(self.logicalChannel)

    def setSrvCtrlId(self, simId):
        self.srvId = simId
        self.setActiveChannel(self.logicalChannel)

    def getSrvCtr(self):
        return self.router.getCardDictFromId(self.srvId)[sim_router.CTRL_INTERFACE]

    def setActiveChannel(self, channel):
        self.setCurrentAidId(None)
        return self.getSrvCtr().setActiveChannel(channel)

    def sendApdu(self, apdu, channel=None, mode=1): # 1-sim_router.INJECT_NO_FORWARD
        #TODO: add 'check=False, sw=0x9000' arguments
        cla = int(apdu[0:2], 16)
        ctrlSrv = self.getSrvCtr()
        mainSrv = self.router.getRelatedMainCard(ctrlSrv)
        if mainSrv.logicalChannelClosed or ctrlSrv.logicalChannelClosed:
            # After e.g. reset, ATR. Logical channel was closed
            self.setLogicalChannel(0)
            mainSrv.logicalChannelClosed = False
            ctrlSrv.logicalChannelClosed = False
        if channel != None:
            logicalChannel = channel
        else:
            logicalChannel = self.getSrvCtr().getActiveChannel()
        if logicalChannel and not cla & 0x0F:
            cla = cla | (logicalChannel & 0x0F)
            apdu = "%02X%s" %(int(cla), apdu[2:])
        rapdu = self.router.injectApdu(apdu, self.getSrvCtr(), mode=mode)
        return types.sw1(rapdu), types.sw2(rapdu), types.responseData(rapdu)

    def getDfGsmResponse(self):
        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.selectFileRoot("7F20")
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.getResponse(length)
        return data

    def pin1Enabled(self):
        length = self.selectAid()
        if not length:
            return None, None

        sw1, sw2, data = self.getResponse(length)
        do = types.parseFcpTlv(data, types.PIN_STATUS_TEMPLETE_DO_TAG)
        psDo = types.parseTlv(do, types.PS_DO_TAG)

        if psDo[0] & 0x80:
            enabled = True
        else:
            enabled = False
        return enabled

    def pin1Status(self):
        #VERIFY
        sw1, sw2, data = self.sendApdu("0020000100")
        if sw1 not in [0x63, 0x98]:
            return None
        attemptsLeft = sw2 & 0x0F
        return attemptsLeft

    def pin1UnblockStatus(self):
        #UNBLOCK_PIN
        sw1, sw2, data = self.sendApdu("002C000100")
        if sw1 != 0x63:
            return None
        attemptsLeft = sw2 & 0x0F
        return attemptsLeft

    def pin1Enable(self, state):
        sw1, sw2, data = self.sendApdu("0028000100")
        if sw1 != 0x63:
            return None

    def pin2Status(self):
        #VERIFY
        sw1, sw2, data = self.sendApdu("0020008100")
        if sw1 != 0x63:
            return None
        attemptsLeft = sw2 & 0x0F
        return attemptsLeft

    def pin2UnblockStatus(self):
        #UNBLOCK_PIN
        sw1, sw2, data = self.sendApdu("002C008100")
        if sw1 != 0x63:
            return None
        attemptsLeft = sw2 & 0x0F
        return attemptsLeft

    def admStatus(self, admId):
        admHexStr = {sim_codes.ADM_1 : '0A', sim_codes.ADM_2 : '0B', sim_codes.ADM_3: '0C', sim_codes.ADM_4 : '0D'}
        #VERIFY
        sw1, sw2, data = self.sendApdu("002000%s00" %admHexStr[admId])
        if sw1 != 0x63:
            return None
        attemptsLeft = sw2 & 0x0F
        return attemptsLeft

    def adm1Status(self):
        return self.admStatus(sim_codes.ADM_1)

    def adm2Status(self):
        return self.admStatus(sim_codes.ADM_2)

    def adm3Status(self):
        return self.admStatus(sim_codes.ADM_3)

    def adm4Status(self):
        return self.admStatus(sim_codes.ADM_4)

    def getResponse(self, length):
        #GET_RESPONSE
        sw1, sw2, data = self.sendApdu("00C00000%02X" %length)
        if not types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            fileDescriptor = types.parseFcpTlv(data, types_g.selectTag.FILE_DESCRIPTOR)
            fileType = fileDescriptor[0]
            self.setCurrentFileType(fileType)
        return sw1, sw2, data

    def selectFile(self, fid):
        #SELECT_FILE
        sw1, sw2, data = self.sendApdu("00A4000402%s" %fid)
        if not types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', log=False):
            self.appendCurrentDir(fid)
        return sw1, sw2, data

    def selectMf(self):
        #SELECT_FILE MF
        return self.selectFile("3F00")

    def selectFileFromMf(self, fids):
        #SELECT_FILE by path from MF
        # fids (set of File IDentifiers) is e.g. '7FFF6F07'.
        sw1, sw2, data = self.sendApdu("00A40804%02X%s" %(len(fids)/2, fids))
        if not types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', log=False):
            self.setCurrentFilePath(self.getPathFromFids(fids))
        return sw1, sw2, data

    def selectParentDir(self):
        #SELECT_FILE
        fid = types.fidFromPath(self.getCurrentDirPath())
        if fid.startswith("ADF") or self.getCurrentFilePath() == "/":
            parentApdu = "00A40004023F00"
        else:
            parentApdu = "00A40304"
        sw1, sw2, data = self.sendApdu(parentApdu)
        error = types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G')
        if error:
            if not types.assertSw(sw1, sw2, checkSw1='REPEAT_COMMAND_WITH_LE'):
                #repeat command with LE
                sw1, sw2, data = self.sendApdu("%s%02X" %(parentApdu, sw2))
                error = types.assertSw(sw1, sw2, checkSw='NO_ERROR')
                #be careful to not use getResponse() before sending select command
        if not error:
            self.decrementCurrentDir()
        return sw1, sw2, data

    def selectFileRoot(self, fid):
        self.selectMf()
        return self.selectFile(fid)

    def selectFileGsm(self, fid):
        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.selectFileRoot("7F20")
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return sw1, sw2, data
        return self.selectFile(fid)

    def getAid(self, aidId=None):
        recordEfDirLength = self.getEfDirRecordStatus()[0]
        if not recordEfDirLength:
            return None

        if aidId == None:
            aidId = self.getCurrentAidId()
            if aidId == None:
                aidId = 0

        #READ RECORD
        sw1, sw2, data = self.sendApdu("00B2%02d04%02X" %(aidId+1, recordEfDirLength))
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return None

        if data.count(0xFF) == len(data):
            #all elements are 0xFF
            return None
        aid = types.getAidFromDirRecord(data)
        return hextools.bytes2hex(aid)

    def findAidRecord(self, aid):
        nbrOfRecords = self.getEfDirRecordStatus()[1]
        for i in range(1, nbrOfRecords + 1):
            if self.getAid(i - 1) == hextools.bytes2hex(aid):
                return i # record index
        return 0

    def selectAid(self, aid=None, aidId=None):
        if aidId == None:
            if self.getCurrentAidId() == None:
                aidId = 0
            else:
                aidId = self.getCurrentAidId()
        if not aid:
            aid = self.getAid(aidId)
            if not aid:
                return None
        apdu = "00A40404%02X%s" %(len(aid)/2, aid)
        #select AID
        sw1, sw2, data = self.sendApdu(apdu)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return None
        if sw2:
            self.setCurrentAidId(aidId)
        self.resetCurrentDir()
        self.appendCurrentDir("ADF%d" %aidId, types_g.fileDescriptor.DF_OR_ADF)
        length = sw2
        return length

    def selectDfHnb(self):
        if not self.selectAid():
            logging.error("Failed to select AID")
            return False
        sw1, sw2, data = self.selectFile("5F50")
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            logging.error("Failed to select DF_HNB")
        return sw1, sw2, data

    def getCurrentFile(self):
        return self.getSrvCtr().getCurrentFile()

    def getCurrentFilePath(self):
        return self.getSrvCtr().getCurrentFilePath()

    def getCurrentFileType(self):
        return self.getSrvCtr().getCurrentFileType()

    def getCurrentDirPath(self):
        return self.getSrvCtr().getCurrentDirPath()

    def setCurrentFile(self, path, type):
        self.getSrvCtr().setCurrentFile(path, type)

    def setCurrentFilePath(self, path):
        self.getSrvCtr().setCurrentFilePath(path)

    def setCurrentFileType(self, type):
        self.getSrvCtr().setCurrentFileType(type)
        self.simFiles.setCurrentDirPath(self.getCurrentDirPath())

    def appendCurrentDir(self, name, type=types_g.fileDescriptor.NO_INFORMATION_GIVEN):
        self.getSrvCtr().appendCurrentDir(name, type)

    def decrementCurrentDir(self):
        self.getSrvCtr().decrementCurrentDir()

    def resetCurrentDir(self):
        self.getSrvCtr().resetCurrentDir()

    def getPathFromFids(self, fids):
        # fids (set of File IDentifiers) is e.g. '7FFF6F07'.
        # A path is a concatenation of FIDs.
        path = '/' + '/'.join([fids[i:i+4] for i in range(0, len(fids), 4)])
        if self.getCurrentAidId() != None:
            path = path.replace("7FFF", "ADF" + str(self.getCurrentAidId()))
        return path

    def readCurrentFileBinary(self, data):
        #READ BINARY
        tagData = types.parseFcpTlv(data, types.FILE_LENGTH_EXCLUDING_SI_TAG)
        if tagData == None:
            logging.error("BINARY_LENGTH_TAG not found in FCI")
            return None, None, None
        length = tagData[1]
        sw1, sw2, data = self.sendApdu("00B000%04X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def readFileBinary(self, fid):
        sw1, sw2, data = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return sw1, sw2, data

        sw1, sw2, data = self.getResponse(sw2)
        if not data:
            return sw1, sw2, data
        sw1, sw2, data = self.readCurrentFileBinary(data)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def getFileStructure(self, data):
        fileDecriptorTag = types.parseFcpTlv(data, types_g.selectTag.FILE_DESCRIPTOR)
        if fileDecriptorTag == None:
            logging.error("FILE_DESCRIPTOR tag not found in FCI")
            return None, None
        fileDecriptor = fileDecriptorTag[0]
        return types.getFileStructureFromFileDescriptor(fileDecriptor)

    def getRecordInfo(self, data):
        fileDecriptorTag = types.parseFcpTlv(data, types_g.selectTag.FILE_DESCRIPTOR)
        if fileDecriptorTag == None:
            logging.error("FILE_DESCRIPTOR tag not found in FCI")
            return None, None
        fileDecriptor = fileDecriptorTag[0]
        if self.getFileStructure(data) == types.FILE_STRUCTURE_TRANSPARENT:
            logging.error("Selected file is transparent")
            return None, None
        recordLength = fileDecriptorTag[3]
        nbrOfRecords = fileDecriptorTag[4]
        return recordLength, nbrOfRecords

    def readCurrentFileRecord(self, data, recordId):
        recordLength, nbrOfRecords = self.getRecordInfo(data)
        if recordId == 0xFF:
            startRecord = 1
            endRecord = nbrOfRecords
        else:
            startRecord = recordId
            endRecord = recordId
        '''
        tagData = self.parseFciTlv(data, types.FILE_LENGTH_EXCLUDING_SI_TAG)
        if tagData == None:
            logging.error("BINARY_LENGTH_TAG not found in FCI")
            return sw1, sw2, []
        length = tagData[1]
        '''
        dataRecord = []
        for id in range(startRecord, endRecord+1):
            sw1, sw2, data = self.sendApdu("00B2%02X04%02X" %(id, recordLength))
            dataRecord.extend([data])
            if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                break
        return sw1, sw2, dataRecord

    def readFileRecord(self, fid, recordId=0xFF):
        sw1, sw2, data = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return sw1, sw2, data

        sw1, sw2, data = self.getResponse(sw2)
        if not data:
            return sw1, sw2, data

        sw1, sw2, data = self.readCurrentFileRecord(data, recordId)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def writeCurrentFileBinary(self, data, value):
        fileLength = types.getFileLength(data)
        value = types.addTrailingBytes(value, 0xFF, fileLength)
        length = len(value)/2
        sw1, sw2, data = self.sendApdu("00D60000%02X%s" %(length, value))
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def writeFileBinary(self, fid, value):
        sw1, sw2, respData = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return False

        sw1, sw2, data = self.writeCurrentFileBinary(respData, value)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def writeCurrentFileRecord(self, respData, records, recordId):
        recordLength, nbrOfRecords = self.getRecordInfo(respData)
        if recordId == 0xFF:
            startRecord = 1
            endRecord = nbrOfRecords
        else:
            startRecord = recordId
            endRecord = recordId
        i = 0
        for id in range(startRecord, endRecord+1):
            if len(records) < i+1:
                record = types.addTrailingBytes('', 0xFF, recordLength)
            else:
                record = types.addTrailingBytes(records[i], 0xFF, recordLength)
            sw1, sw2, data = self.sendApdu("00DC%02X04%02X%s" %(id, recordLength, record))
            if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                break
            i += 1
        return sw1, sw2, data

    def writeFileRecord(self, path, value, recordId=0xFF):
        sw1, sw2, data = self.selectFileByPath(path)
        if not data:
            return False
        fid = types.fidFromPath(path)
        sw1, sw2, data = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return False
        sw1, sw2, data = self.getResponse(sw2)
        sw1, sw2, data = self.writeCurrentFileRecord(data, value, recordId)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def getAdfId(self, fid):
        adfId = None
        fileFormat = types.getFileNameFormat(fid)
        if fileFormat == types.FILE_FORMAT_ADF_ID:
            adfId = types.getAdfId(fid)
        elif fileFormat == types.FILE_FORMAT_ADF_NAME:
            adfId = types.getAdfId(self.simFiles.getAdfId(fid))
        return adfId

    def selectFileByPath(self, path):
        sw2 = None
        if not path or path[0] != "/":
            raise Exception("Invalid format for path: " + path)

        if path in ["/", "/3F00"]:
            sw1, sw2, data = self.selectMf()
        else:
            files = types.getFilesFromPath(path)
            for _file in files:
                if "ADF" in _file:
                    adfId = self.getAdfId(_file)
                    if adfId == None:
                        logging.error("Invalid ADF id")
                        return None, None, []
                    if adfId != self.getCurrentAidId():
                        # Select ADF using id.
                        sw2 = self.selectAid(aidId=adfId)
                        if not sw2:
                            logging.error("Failed to select AID")
                            return None, None, []
                    path = path.replace(_file, "7FFF")
                    break # handle only the first occurence of ADF
            # Select file using its absolute path (starting from MF).
            path = path.replace("/", "")
            path = path.replace("3F00", "")
            sw1, sw2, data = self.selectFileFromMf(path)
            if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
                return sw1, sw2, []
        # Update current dir type based on response.
        sw1, sw2, data = self.getResponse(sw2)
        return sw1, sw2, data

    def listFiles(self):
        path = self.getCurrentDirPath()
        if path == "/":
            path = "3F00"
        path += "/"
        fidCurrentDir =  types.fidFromPath(path)
        formatCurrentDir = types.getFileNameFormat(fidCurrentDir)
        if formatCurrentDir == types.FILE_FORMAT_ADF_ID:
            fidCurrentDir = "7FFF" #current aid
        filesToCheck = self.simFiles.findAllChildFiles(path)
        files = []
        for file in filesToCheck:
            fid =  types.fidFromPath(file)
            format = types.getFileNameFormat(file)
            if format == types.FILE_FORMAT_ADF_NAME:
                fid = self.simFiles.getAdfId(fid)
                if fid:
                    files.append(file)
                #no update of current dir is needed. Just continue
                continue
            sw1, sw2, data = self.selectFile(fid)
            if sw1 != types_g.sw1.RESPONSE_DATA_AVAILABLE_3G:
                continue
            files.append(file)
            sw1, sw2, data = self.selectFile(fidCurrentDir)
            if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
                raise Exception("Failed to select current dir")
        return files

    def readFile(self, file):
        sw1, sw2, data = self.selectFileByPath(file)
        if not data:
            logging.error("Failed to select: %s" %file)
            return None, None, []
        structure = self.getFileStructure(data)

        if structure in [types.FILE_STRUCTURE_LINEAR_FIXED, types.FILE_STRUCTURE_CYCLIC]:
            sw1, sw2, data = self.readCurrentFileRecord(data, recordId=0xFF)
        else:
            sw1, sw2, data = self.readCurrentFileBinary(data)
        return sw1, sw2, data

    def readFileData(self, file):
        sw1, sw2, data = self.readFile(file)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return None
        if not isinstance(data[0], list):
            str = "%s" %hextools.bytes2hex(data)
        else:
            str = ''
            for record in data:
                str += "%s;" %hextools.bytes2hex(record)
            str.strip(";")
        return str

    def writeFile(self, file, value):
        sw1, sw2, respData = self.selectFileByPath(file)
        if not respData:
            logging.error("Failed to select: %s" %file)
            return None
        structure = self.getFileStructure(respData)
        if structure in [types.FILE_STRUCTURE_LINEAR_FIXED, types.FILE_STRUCTURE_CYCLIC]:
            value = value.split(';')
            sw1, sw2, data = self.writeCurrentFileRecord(respData, value, recordId=0xFF)
        else:
            sw1, sw2, data = self.writeCurrentFileBinary(respData, value)
        return sw1, sw2, data

    def writeFileData(self, file, value):
        sw1, sw2, data = self.writeFile(file, value)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def getLinkedArrFile(self, path):
        sw1, sw2, data = self.selectFileByPath(path)
        if not data:
            logging.error("Failed to select: %s" %path)
            return None, None
        return types.getArrFileFromData(data)

    def getSecurityAttrib(self, path):
        sw1, sw2, data = self.selectFileByPath(path)
        if not data:
            logging.error("Failed to select: %s" %path)
            return None
        return types.getSecurityAttribFromData(data)

    """
    def getConditions(self, path, accessMode):
        arrRecord, arrValue = self.getArrRecordForFile(path)
        if not (arrValue and arrRecord):
            # Try with Expanded SE
            arrValue = types.getSecurityAttrib(path)
            if not arrValue:
                return [types.AC_UNKNOWN], None

        conditions, mode = types.getAccessConditions(arrValue, accessMode)
        return conditions, mode
    """

    def removeAccessMode(self, val, mode, tag):
        for i, byte in enumerate(val, start=0):
            if byte == tag and (val[i+types.AM_BYTE_OFFSET] & mode):
                logging.debug("Remove old rule for chosen access mode")
                val[i+types.AM_BYTE_OFFSET] &= ~mode
                if not val[i+types.AM_BYTE_OFFSET]:
                    #no more accessModes are using this rule, lets remove it
                    logging.debug("Removing obsolete rule.")
                    #first calculate how many bytes we are going to remove
                    erase = 4 + val[i+types.AM_LENGTH_OFFSET]
                    if val[i+types.SC_DO_OFFSET]:
                        erase = erase + val[i+types.SC_DO_LENGTH_OFFSET]
                    #remove those bytes from value and append 0xFF
                    for tempIndex in range(i, i+erase):
                        val.pop(i)
                        val.append(0xFF)
        return val

    def updateArrRule(self, val, condition, mode, tag, key):
        found = False
        #simple case, no user authentication needed
        if condition == types.AC_ALWAYS:
            for i, byte in enumerate(val, start=0):
                #look for SC_DO_ALWAYS setup
                if (byte == tag and \
                    val[i+types.SC_DO_OFFSET] == types.SC_DO_ALWAYS):
                    #add set corresponding mode bit
                    logging.debug("SC_DO_ALWAYS - add to existing rule")
                    found = True
                    val[i+types.AM_BYTE_OFFSET] |= mode
        #all other cases than AC_NEVER condition
        elif condition != types.AC_NEVER:
            for i, byte in enumerate(val, start=0):
                #look for tag and SC_DO_USER_AUTH_QC tag
                if (byte == tag and \
                    val[i+types.SC_DO_OFFSET] == types.SC_DO_USER_AUTH_QC and \
                    val[i+types.KEY_DO_VALUE_OFFSET] == key):
                    logging.debug("SC_DO_USER_AUTH_QC - add to existing rule")
                    found = True
                    val[i+types.AM_BYTE_OFFSET] |= mode
        return found, val

    def createArrRule(self, oldValue, value, record, condition, mode, tag, key):
        #check needed space
        if condition == types.AC_ALWAYS:
            length = 5
        elif condition in [types.AC_NEVER,
                           types.AC_UNKNOWN]:
            length = 0
        elif condition in [types.AC_CHV1,
                           types.AC_CHV2,
                           types.AC_RFU,
                           types.AC_ADM1,
                           types.AC_ADM2,
                           types.AC_ADM3,
                           types.AC_ADM4,
                           types.AC_ADM5]:
            length = 15
        #calculate free space
        freeSpace = value.count(0xFF)
        #check if there is enough space in efArr register
        if freeSpace >= length:
            #put new rule in place of first 0xFF byte
            logging.debug("Creating new rule")
            index = list(value).index(0xFF)
            value[index] = tag
            value[index+types.AM_LENGTH_OFFSET] = 1
            value[index+types.AM_BYTE_OFFSET] = mode
            if condition == types.AC_ALWAYS:
                value[index+types.SC_DO_OFFSET] = key
                value[index+types.SC_DO_LENGTH_OFFSET] = 0
            else:
                value[index+types.SC_DO_OFFSET] = types.SC_DO_USER_AUTH_QC
                value[index+types.SC_DO_LENGTH_OFFSET] = 3
                value[index+types.KEY_REF_TAG_OFFSET] = types.KEY_REF_TAG
                value[index+types.KEY_DO_LENGTH_OFFSET] = 1
                value[index+types.KEY_DO_VALUE_OFFSET] = key
        else:
            #if there is not enough free space, reset all modifications
            logging.warning("Not enough free space to write new rule")
            return oldValue
        return value

    def setArrCondition(self, arrFile, record, value, mode, condition):
        oldValue = value
        key = types.keyRefDict[condition]
        found = False
        if mode in [types.AM_EF_DELETE,
                    types.AM_EF_TERMINATE,
                    types.AM_EF_ACTIVATE,
                    types.AM_EF_DEACTIVATE,
                    types.AM_EF_WRITE,
                    types.AM_EF_UPDATE,
                    types.AM_EF_READ]:
            tag = types.AM_DO_BYTE
        elif mode in [types.AM_EF_INCREASE, types.AM_EF_RESIZE]:
            tag = types.AM_DO_INS
        else:
            logging.error("Chosen access mode %s not implemented" %mode)
            return False
        value = self.removeAccessMode(value, mode, tag)
        found, value = self.updateArrRule(value, condition, mode, tag, key)
        #no rule found for our setup, lets make new rule
        if not found and condition != types.AC_NEVER:
            value = self.createArrRule(oldValue, value, record, condition, mode, tag, key)
        value = hextools.bytes2hex(value)
        status = self.writeFileRecord(arrFile, [value], record)
        return status

    def getArrRecordForFile(self, path):
        arrFileId, arrRecord = self.getLinkedArrFile(path)
        if not arrFileId:
            return None, None
        if arrRecord == 0:
            #TODO: check if correct
            logging.warning("Arr record number is 0 for file: " + path +
                            ". Use first record (1) instead.")
            arrRecord = 1
        if types.cmpBitwise(self.getCurrentFileType(), types_g.fileDescriptor.DF_OR_ADF):
            sw1, sw2, data = self.selectParentDir()
            if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', log=False) and \
                types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                logging.error("Failed to select parent dir")
                return None, None

        sw1, sw2, data = self.readFileRecord(arrFileId, arrRecord)
        sw1Name, swReceived = types.swName(sw1, sw2)
        if swReceived == 'FILE_NOT_FOUND':
            # Searching for EF_ARR in parent dir.
            # FIXME: it may never enter here as the Arr file is selected
            #        by FID and it will be searched in parent DF as well.
            sw1, sw2, data = self.selectParentDir()
            if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', log=False) and \
                types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                logging.error("Failed to select parent dir")
                return None, None

            sw1, sw2, data = self.readFileRecord(arrFileId, arrRecord)
            sw1Name, swReceived = types.swName(sw1, sw2)
            if swReceived == 'FILE_NOT_FOUND':
                logging.warning("EF_ARR not found in parent dir")
                return None, None
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return None, None
        arrValue = data[0]
        return arrRecord, arrValue

    def setConditions(self, arrFile, record, value=types.ARR_ALL_ALWAYS):
        status = self.writeFileRecord(arrFile, [hextools.bytes2hex(value)], record)
        return status

    def pin1Verified(self):
        status = False
        # Save current file path
        currentPath = self.getCurrentFilePath()

        # Custom procedure for checking access condition
        # Try to read /ADF0/EF_IMSI file
        if not self.selectAid():
            logging.error("Failed to select AID")
            status = False
        else:
            sw1, sw2, data = self.readFileBinary("6F07")
            sw1Name, swName = types.swName(sw1, sw2)

            if swName in ['ACCESS_CONDITION_NOT_FULFILLED',
                          'UNSUCCESSFUL_USER_PIN_VERIFICATION',
                          'SECURITY_STATUS_NOT_SATISFIED']:
                status = False
            elif swName == 'NO_ERROR' or sw1 == types_g.sw1.NO_ERROR_PROACTIVE_DATA:
                status = True
            else:
                logging.error("SW:'%s' not expected" %swName)
                status = None

        # Restore path selection
        self.selectFileByPath(currentPath)

        return status

    def getImsiCache(self):
        return self.getSrvCtr().imsi

    def getCurrentAidId(self):
        return self.getSrvCtr().getCurrentAidId()

    def setCurrentAidId(self, aidId):
        return self.getSrvCtr().setCurrentAidId(aidId)

    def getAd(self):
        if not self.selectAid():
            logging.error("Failed to select AID")
            return None

        sw1, sw2, data = self.readFileBinary("6FAD")
        return data

    def setAd(self, data):
        if not self.selectAid():
            logging.error("Failed to select AID")
            return False
        return self.writeFileBinary("6FAD", data)

    def getGid1(self):
        if not self.selectAid():
            logging.error("Failed to select AID")
            return None

        sw1, sw2, data = self.readFileBinary("6F3E")
        return hextools.bytes2hex(data)

    def setGid1(self, data):
        currentData = self.getGid1()
        data = types.addTrailingBytes(data, 0xFF, len(currentData)/2)
        return self.writeFileBinary("6F3E", data)

    def getAcsglRaw(self):
        sw1, sw2, data = self.selectDfHnb()
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return sw1, sw2, data
        return self.readFileRecord("4F81", recordId=0xFF)

    def getAcsgl(self):
        sw1, sw2, data = self.getAcsglRaw()
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return None
        str = ''
        for record in data:
            str += "%s;" %hextools.bytes2hex(record)
        return str

    def getiAcsgl(self):
        sw1, sw2, data = self.getAcsglRaw()
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return None
        dataStr = ''
        for record in data:
            plmn = types.parseCsgTlv(record, types.CSG_PLMN_TAG)
            csgInformation = types.parseCsgTlv(record, types.CSG_INFORMATION_TAG)
            if not plmn or not csgInformation:
                continue
            mnc3 = plmn[1] >> 4
            plmnRaw = hextools.decode_BCD(plmn)
            mcc = plmnRaw[0:3]
            if mnc3 != 0x0F:
                mnc = plmnRaw[4:6]
                mnc = mnc + str(mnc3)
            else:
                mnc = plmnRaw[3:5]
            csgType = csgInformation[0]
            hnbNameInd = csgInformation[1]
            csgId = hextools.bytes2hex(csgInformation[2:])
            csgId = int(csgId, 16) >> 5
            dataStr += "plmn=%s,csg_type=%02X,hnb_name_ind=%02X,csg_id=%02X;" %(mcc+mnc, csgType, hnbNameInd, csgId)
        dataStr = dataStr.rstrip(";")
        if not dataStr:
            dataStr = "EMPTY"
        return dataStr

    def setAcsgl(self, data):
        currentData = self.getAcsgl()
        if not currentData:
            return False
        recordLength = len(currentData.split(';')[0]) / 2

        records = data.split(';')
        data = []
        for record in records:
            dataTmp = types.addTrailingBytes(record, 0xFF, recordLength)
            data.append(dataTmp)
        return self.writeFileRecord("4F81", data, recordId=0xFF)

    def setiAcsgl(self, records):
        sw1, sw2, data = self.getAcsglRaw()
        recordLength = len(data[0])
        records = records.split(';')
        data = []
        for record in records:
            dataTmp = ''#types.addTrailingBytes('', 0xFF, recordLength)
            plmn = types.getParamValue(record, "plmn")
            csgType = types.getParamValue(record, "csg_type")
            if not csgType:
                csgType = "00"
            hnbNameInd = types.getParamValue(record, "hnb_name_ind")
            if not hnbNameInd:
                hnbNameInd = "00"
            csgId = types.getParamValue(record, "csg_id")

            if not plmn or not csgId:
                return False

            plmnLength = len(plmn)
            if plmnLength not in [5,6]:
                logging.error("Incorrect plmn length:%d" %len(plmn))
                return False
            elif plmnLength == 6:
                mnc3 = plmn[5]
            else:
                mnc3 = 'F'
            plmnBcd = hextools.encode_BCD(plmn[0:3] + mnc3 + plmn[3:5])
            plmnCoded = hextools.bytes2hex(plmnBcd)
            csgIdData = (int(csgId, 16) << 5) | 0b00011111
            csgInformation = "%02X%02X%08X" %(int(csgType, 16), int(hnbNameInd, 16), csgIdData)

            dataTmp = types.addTlv(dataTmp, types.CSG_PLMN_TAG, plmnCoded)
            dataTmp = types.addTlv(dataTmp, types.CSG_INFORMATION_TAG, csgInformation)
            dataTmp = types.addMainTlv(dataTmp, types.CSG_TEMPLATE_TAG)
            data.append(dataTmp)
        return self.writeFileRecord("4F81", data, recordId=0xFF)

    def getEfDirRecordStatus(self):
        #select EF_DIR
        sw1, sw2, data = self.selectFileRoot("2F00")
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return None, None
        length = sw2

        sw1, sw2, data = self.getResponse(length)
        if not data:
            return None, None
        return self.getRecordInfo(data) # recordLength, nbrOfRecords

    def addApplication(self, aidId, aid = types.DEFAULT_APP_AID, label = types.DEFAULT_APP_LABEL):
        data = []
        # Aid
        types.addTlv(data, types.APP_IDENTIFIER_TAG, aid)
        # Label
        _label = bytearray()
        _label.extend(label)
        types.addTlv(data, types.APP_LABEL_TAG, _label)
        dataHex = hextools.bytes2hex(data)
        dataHex = types.addMainTlv(dataHex, types.APP_TEMPLATE_TAG)

        recordNum = self.findAidRecord(aid)
        if recordNum:
            logging.error("Aid: %s alredy exists in EF_DIR record: %d"
                          % (hextools.bytes2hex(aid), recordNum))
            return False

        # add a new record at the EOF
        status = self.addEfDirRecord(dataHex)

        self.simFiles.resolveAdfs(self.readFileData('/2F00'))
        return status

    def removeApplication(self, aidId):
        recordNum = aidId + 1
        nbrOfRecords = self.getEfDirRecordStatus()[1]

        if recordNum > nbrOfRecords:
            logging.error("Number of records exceeded")
            return False

        if recordNum < nbrOfRecords:
            status = self.setEfDirRecord(recordNum, "") # fill with 'FF'
        else:
            status = self.removeEfDirRecord() # remove last record
        self.simFiles.resolveAdfs(self.readFileData('/2F00'))
        return status

    def addEfDirRecord(self, value=None):
        recordLength, nbrOfRecords = self.getEfDirRecordStatus()
        self.selectMf()
        newSize = (nbrOfRecords + 1) * recordLength
        data = None
        if value:
            data = bytearray.fromhex(value)
        path = "/2F00"
        status = self.resizeFile(path, newSize, data)
        return status

    def removeEfDirRecord(self):
        recordLength, nbrOfRecords = self.getEfDirRecordStatus()
        self.selectMf()
        if nbrOfRecords:
            newSize = (nbrOfRecords - 1) * recordLength
        else:
            return False
        path = "/2F00"
        status = self.resizeFile(path, newSize)
        return status

    def setEfDirRecord(self, recordNum, value):
        self.selectMf()
        path = "/2F00"
        status = self.writeFileRecord(path, [value], recordNum)
        return status

    def checkDfHnb(self):
        sw1, sw2, data = self.selectDfHnb()
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return False
        return True

    def checkEfAcsgl(self):
        sw1, sw2, data = self.selectDfHnb()
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return False
        sw1, sw2, data = self.getAcsglRaw()
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def createDfHnb(self):
        if not self.selectAid():
            logging.error("Failed to select AID")
            return None
        sw1, sw2, data = self.sendApdu("00E000001E621C8202782183025F508A01058B036F060481020001C606900100950100")
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def createEfAcsgl(self):
        if not self.selectAid():
            logging.error("Failed to select AID")
            return None

        sw1, sw2, data = self.selectDfHnb()
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            return False
        sw1, sw2, data = self.sendApdu("00E000001A621882044221002083024F818A01058B036F0603800200608800")
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def verifyCode(self, pinId, code=None):
        verify = types_g.iso7816.VERIFY_PIN
        newCode = ""
        length = 0x08
        if pinId == sim_codes.PIN_1:
            chvP2 = types_g.verifyChvP2_3g.chv1
        elif pinId == sim_codes.PIN_1_UNBLOCK:
            chvP2 = types_g.verifyChvP2_3g.chv1
            verify = types_g.iso7816.UNBLOCK_PIN
            length = 0x10
            newCode = sim_codes.defaultCard[sim_codes.PIN_1]
            newCode = types.addTrailingBytes(newCode.encode("hex"), 0xFF, 8)
        elif pinId == sim_codes.PIN_1_ENABLE:
            chvP2 = types_g.verifyChvP2_3g.chv1
            verify = types_g.iso7816.ENABLE_PIN
        elif pinId == sim_codes.PIN_1_DISABLE:
            chvP2 = types_g.verifyChvP2_3g.chv1
            verify = types_g.iso7816.DISABLE_PIN
        elif pinId == sim_codes.PIN_2:
            chvP2 = types_g.verifyChvP2_3g.chv2
        elif pinId == sim_codes.PIN_2_UNBLOCK:
            chvP2 = types_g.verifyChvP2_3g.chv2
            verify = types_g.iso7816.UNBLOCK_PIN
            length = 0x10
            newCode = sim_codes.defaultCard[sim_codes.PIN_2]
            newCode = types.addTrailingBytes(newCode.encode("hex"), 0xFF, 8)
        elif pinId == sim_codes.ADM_1:
            chvP2 = types_g.verifyChvP2_3g.adm1
        elif pinId == sim_codes.ADM_4:
            chvP2 = types_g.verifyChvP2_3g.adm4
        else:
            raise Exception("PinId: %02X invalid" %pinId)


        if not code:
            code = sim_codes.defaultCard[pinId]
        #VERIFY
        code = types.addTrailingBytes(code.encode("hex"), 0xFF, 8)
        sw1, sw2, data = self.sendApdu("00%02X00%02X%02X%s%s" %(verify, chvP2, length, code, newCode))

        sw1Name, swName = types.swName(sw1, sw2)
        if swName == 'NO_ERROR' or sw1 == types_g.sw1.NO_ERROR_PROACTIVE_DATA:
            logging.info("Verification success")
        elif swName == 'REFERNCE_DATA_INVALIDATE':
            logging.warning("PIN is disabled")
        elif swName == 'WARNING_CARD_STATE_UNCHANGED':
            logging.warning("PIN already disabled/enabled")
        elif swName == 'AUTHENTICATION_METHOD_BLOCKED':
            logging.warning("PIN is blocked!")
        elif sw1Name == 'CODE_ATTEMPTS_LEFT':
            logging.error("Verify failed! Attempts left: %d" %(sw2 & 0x0F))
            return False
        else:
            logging.error("SW:'%s' not expected" %swName)
            return False
        return True

    def openChannel(self, originChannel, targetChannel):
        #OPEN_CHANNEL
        length = 0
        if targetChannel == 0:
            length = 1 #  returns the number of assigned channel
        sw1, sw2, data = self.sendApdu("0%01X7000%02X%02X" %(originChannel, targetChannel, length))
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False

        if length:
            return data[0]
        else:
            return targetChannel

    def closeChannel(self, originChannel, targetChannel, log=True):
        #CLOSE_CHANNEL
        sw1, sw2, data = self.sendApdu("0%01X7080%02X00" %(originChannel, targetChannel))
        if log:
            types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        if types.packSw(sw1, sw2) != types_g.sw.NO_ERROR:
            return False
        if self.logicalChannel == targetChannel:
            self.setLogicalChannel(0)
        # TODO: current ID and current dir shall be assigned to logical channel.
        self.setCurrentAidId(None) # reset last selected aid
        self.selectMf() # reset current dir
        return True

    def createDirectory(self,
                        path,
                        shareable=True,
                        LcsiValue=0x05,
                        se01=0x03,
                        totalFileSize=0x64,
                        aid=types.DEFAULT_APP_AID):
        logging.debug("Creating directory: %s" %path)
        # Select parent dir
        parentPath = types.parentDirFromPath(path)
        sw1, sw2, data = self.selectFileByPath(parentPath)
        if not data:
            logging.error("Failed to select parent dir: %s" %parentPath)
            return False

        fid = types.fidFromPath(path)
        fidInt = int(fid, 16)
        fidLowByte = fidInt & 0xFF
        fidHighByte = (fidInt & 0xFF00) >> 8
        data = []
        fileDescriptionByte = types_g.fileDescriptor.DF_OR_ADF
        if shareable:
            fileDescriptionByte |= types_g.fileDescriptor.SHAREABLE
        types.addTlv(data, types.FDB_TAG, [fileDescriptionByte,
                                           types.DATA_CODING_BYTE])
        types.addTlv(data, types.FID_TAG, [fidHighByte,
                                                       fidLowByte])

        if fid.lower().startswith('adf'):
            # Tag '84' shall only be present for an ADF
            if aid != None:
                types.addTlv(data, types.DF_NAME_TAG, aid)
            else:
                return False

        types.addTlv(data, types.LCSI_TAG, [LcsiValue])
        if parentPath in ["/3F00", "/"]:
            efArr = types.EF_ARR_MF
        else:
            efArr = types.EF_ARR
        arrHighByte = efArr >> 8
        arrLowByte = efArr & 0xFF
        #TODO: check why SECURITY_ATTRIB_REF_EXPANDED is invalid
        types.addTlv(data, types.SECURITY_ATTRIB_COMPACT_TAG, [arrHighByte,
                                                       arrLowByte,
                                                       se01])
        types.addTlv(data, types.TOTAL_FILE_SIZE_TAG, [totalFileSize >> 8,
                                                   totalFileSize & 0xFF])
        types.addTlv(data, types.PIN_STATUS_TEMPLETE_DO_TAG, [types.PS_DO_TAG,
                                                   0])
        #TODO: handle DF_AID in proprietary tag 'A5' (for Gemalto)
        '''
        # DF AID Tag = 84h (O) - Only applies to ADFs
        if fid.lower().startswith('adf'):
            tlvData = []
            types.addTlv(tlvData, types.DF_NAME_TAG, aid)
            types.addTlv(data, types.PROPRIETARY_TAG, tlvData)
        '''
        dataHex = hextools.bytes2hex(data)
        dataHex = types.addMainTlv(dataHex, types.FCP_TEMPLATE_TAG)
        header = [0x00, 0xE0, 0x00, 0x00, len(dataHex)/2]
        command = hextools.bytes2hex(header) + dataHex
        logging.debug("createDirectory: %s" %command)
        sw1, sw2, data = self.sendApdu("%s" %command)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        self.appendCurrentDir(fid, types_g.fileDescriptor.DF_OR_ADF)
        logging.debug("Directory: %s created" %path)
        return True

    def createFile(self,
                   path,
                   shareable,
                   fileType,
                   fileSize,
                   recordLength,
                   LcsiValue,
                   se01,
                   sfi):
        logging.debug("Creating file: %s" %path)
        # Select parent dir
        parentPath = types.parentDirFromPath(path)
        sw1, sw2, data = self.selectFileByPath(parentPath)
        if not data:
            logging.error("Failed to select parent dir: %s" %parentPath)
            return False

        fid = types.fidFromPath(path)
        fidInt = int(fid, 16)
        fidLowByte = fidInt & 0xFF
        fidHighByte = (fidInt & 0xFF00) >> 8
        fileDescriptionByte = fileType
        if shareable:
            fileDescriptionByte |= types_g.fileDescriptor.SHAREABLE
        data = []
        array = [fileDescriptionByte, types.DATA_CODING_BYTE]
        if fileType != types_g.fileDescriptor.TRANSPARENT_STRUCTURE:
            array.append(recordLength >> 8)
            array.append(recordLength & 0xFF)
        types.addTlv(data, types.FDB_TAG, array)
        types.addTlv(data, types.FID_TAG, [fidHighByte,
                                                       fidLowByte])
        types.addTlv(data, types.LCSI_TAG, [LcsiValue])

        if parentPath in ["/3F00", "/"]:
            efArr = types.EF_ARR_MF
        else:
            efArr = types.EF_ARR
        arrHighByte = efArr >> 8
        arrLowByte = efArr & 0xFF
        #TODO: check why SECURITY_ATTRIB_REF_EXPANDED is invalid
        types.addTlv(data, types.SECURITY_ATTRIB_COMPACT_TAG, [arrHighByte,
                                                       arrLowByte,
                                                       se01])
        types.addTlv(data, types.FILE_SIZE_TAG, [fileSize >> 8,
                                                 fileSize & 0xFF])
        types.addTlv(data, types.SFI_TAG, [])
        dataHex = hextools.bytes2hex(data)
        dataHex = types.addMainTlv(dataHex, types.FCP_TEMPLATE_TAG)
        header = [0x00, 0xE0, 0x00, 0x00, len(dataHex)/2]
        command = hextools.bytes2hex(header) + dataHex
        sw1, sw2, data = self.sendApdu("%s" %command)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        self.appendCurrentDir(fid)
        logging.debug("File: %s created" %path)
        return True

    def createArrFile(self,
                  path,
                  value,
                  shareable,
                  LcsiValue,
                  nbrOfRecords,
                  recordSize,
                  securityType=types.SECURITY_ATTRIB_EXPANDED_TAG,
                  se01ValueTag=types.FILLING_PATTERN):
        logging.debug("Creating ARR: %s" %path)
        # Select parent dir
        parentPath = types.parentDirFromPath(path)
        sw1, sw2, data = self.selectFileByPath(parentPath)
        if not data:
            logging.error("Failed to select parent dir: %s" %parentPath)
            return False

        fid = types.fidFromPath(path)
        fidInt = int(fid, 16)
        fidLowByte = fidInt & 0xFF
        fidHighByte = (fidInt & 0xFF00) >> 8
        data = []
        fileDescriptionByte = types_g.fileDescriptor.LINEAR_FIXED_STRUCTURE
        if shareable:
            fileDescriptionByte |= types_g.fileDescriptor.SHAREABLE
        types.addTlv(data, types.FDB_TAG, [fileDescriptionByte,
                                           types.DATA_CODING_BYTE,
                                           recordSize >> 8,
                                           recordSize & 0xFF])
        types.addTlv(data, types.FID_TAG, [fidHighByte,
                                                       fidLowByte])
        types.addTlv(data, types.LCSI_TAG, [LcsiValue])
        fillWithPattern = False
        if securityType == types.SECURITY_ATTRIB_EXPANDED_TAG:
            # doesn't work for ISIM cards
            types.addTlv(data, types.SECURITY_ATTRIB_EXPANDED_TAG, value)
        else: # types.SECURITY_ATTRIB_COMPACT_TAG:
            # doesn't work for TWIST cards
            fillWithPattern = True
            if parentPath in ["/3F00", "/"]:
                efArr = types.EF_ARR_MF
            else:
                efArr = types.EF_ARR
            arrHighByte = efArr >> 8
            arrLowByte = efArr & 0xFF
            se01 = 1 # record number - hardcoded
            types.addTlv(data, types.SECURITY_ATTRIB_COMPACT_TAG, [arrHighByte,
                                                           arrLowByte,
                                                           se01])
        totalFileSize = nbrOfRecords * recordSize
        types.addTlv(data, types.FILE_SIZE_TAG, [totalFileSize >> 8,
                                                 totalFileSize & 0xFF])
        if fillWithPattern:
            # First record will be filled with a pattern
            tlvData = []
            types.addTlv(tlvData, se01ValueTag, value)
            types.addTlv(data, types.PROPRIETARY_TAG, tlvData)
        dataHex = hextools.bytes2hex(data)
        dataHex = types.addMainTlv(dataHex, types.FCP_TEMPLATE_TAG)
        header = [0x00, 0xE0, 0x00, 0x00, len(dataHex)/2]
        command = hextools.bytes2hex(header) + dataHex
        logging.debug("create ARR: %s" %command)
        sw1, sw2, data = self.sendApdu("%s" %command)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False, types.packSw(sw1, sw2)
        self.appendCurrentDir(fid)
        logging.debug("EF_ARR: %s created" %path)
        for i in range(1, nbrOfRecords + 1):
            status = self.setConditions(path, record=i, value=value)
            if not status:
                return False, None
        return True, None

    def deleteFile(self, path):
        fid = types.fidFromPath(path)
        if not fid:
            return False
        sw1, sw2, data = self.selectFileByPath(path)
        if not data:
            logging.error("Failed to select: %s" %path)
            return False

        if fid.startswith("ADF"):
            fid = "7FFF"
        # Select the parent dir of the DF as for some cards
        # the DF cannot be deleted if it set as the current file.
        if types.cmpBitwise(self.getCurrentFileType(), types_g.fileDescriptor.DF_OR_ADF):
            sw1, sw2, data = self.selectParentDir()
            if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G', log=False) and \
                types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                logging.error("Failed to select parent dir")
                return False
        else:
            # Select parent dir of the EF
            parentPath = types.parentDirFromPath(path)
            sw1, sw2, data = self.selectFileByPath(parentPath)
            if not data:
                logging.error("Failed to select parent dir: %s" %parentPath)
                return False
        sw1, sw2, data = self.sendApdu("00E4000002%s" %fid)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    '''
    EXTEND_FILE (0xD4) - Gemalto Sim cards
    The same INS as RESIZE_FILE but is handled differently.
    Note: You cannot extend DFs, the MF, Cyclic EFs.
    The size of the file cannot be decreased.
    '''
    def extendFile(self,
                  path,
                  sizeToExtend):
        logging.debug("Extending file: %s" %path)
        sw1, sw2, respData = self.selectFileByPath(path)
        if not respData:
            logging.error("Failed to select: %s" %path)
            return False

        fid = types.fidFromPath(path)
        fidInt = int(fid, 16)
        fidLowByte = fidInt & 0xFF
        fidHighByte = (fidInt & 0xFF00) >> 8
        '''
        The data defining the extension:
            Byte 1-2: Identifier of the file to be extended.
            Byte 3:   Specifies the size or the number of records of the extension.
                      Transparent EF: size of extension (max = 255)
                      Linear Fixed EF: number of records (max = 254)
        '''
        data = [fidHighByte, fidLowByte, sizeToExtend >> 8, sizeToExtend & 0xFF]
        dataHex = hextools.bytes2hex(data)
        header = [0x00, types_g.iso7816.RESIZE_FILE, 0x00, 0x00, len(dataHex)/2]
        command = hextools.bytes2hex(header) + dataHex
        sw1, sw2, data = self.sendApdu("%s" %command)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True

    def resizeFile(self,
                  path,
                  size,
                  pattern=None):
        logging.debug("Resizing file: %s" %path)
        sw1, sw2, respData = self.selectFileByPath(path)
        if not respData:
            logging.error("Failed to select: %s" %path)
            return None

        fid = types.fidFromPath(path)
        fidInt = int(fid, 16)
        fidLowByte = fidInt & 0xFF
        fidHighByte = (fidInt & 0xFF00) >> 8
        data = []

        types.addTlv(data, types.FID_TAG, [fidHighByte, fidLowByte])
        if types.cmpBitwise(self.getCurrentFileType(), types_g.fileDescriptor.DF_OR_ADF):
            types.addTlv(data, types.TOTAL_FILE_SIZE_TAG, [size >> 8, size & 0xFF])
        else:
            types.addTlv(data, types.FILE_SIZE_TAG, [size >> 8, size & 0xFF])
        if pattern:
            tlvData = []
            types.addTlv(tlvData, types.FILLING_PATTERN, pattern)
            types.addTlv(data, types.PROPRIETARY_TAG, tlvData)
        dataHex = hextools.bytes2hex(data)
        dataHex = types.addMainTlv(dataHex, types.FCP_TEMPLATE_TAG)
        header = [0x80, types_g.iso7816.RESIZE_FILE, 0x00, 0x00, len(dataHex)/2]
        command = hextools.bytes2hex(header) + dataHex
        sw1, sw2, data = self.sendApdu("%s" %command)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True
