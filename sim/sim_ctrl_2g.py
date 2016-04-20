#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz

import logging
from util import hextools
from util import types_g
from util import types
import sim_codes
import sim_reader
import file_parser
import sim_router
from sim import sim_files

SIM_ID_0 = 0
SIM_ID_ALL = 0xFF

logicalChannel = 0
INIT_CONTROL_CHANNEL = True


class CurrentFile(object):
    def __init__(self):
        self.path = "/"
        self.type = types_g.fileDescriptor.DF_OR_ADF

class SimCtrl(object):
    def __init__(self, router):
        self.router = router
        self.logicalChannel = 0x00
        self.currentFile = CurrentFile()
        self.file_parser = file_parser.FileParser()
        self.simFiles = sim_files.SimFiles(self.router.simType)
        self.setSrvCtrlId(0)
        self.init()

    def init(self):
        if INIT_CONTROL_CHANNEL:
            self.initLogicalChannels()

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

            '''
            #Check if logical channel supports PIN verify. If not consider logical channel as
            #not supporting all features and close it
            if not self.verifyChannel(channelTmp):
                logging.info("Close deafult logical channel %d" %channelTmp)
                channel = None
                break
            '''
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
        '''
        sw1 = self.sendApdu("A%01X20000100" %channel)[0]
        if sw1 != types_g.sw1.CODE_ATTEMPTS_LEFT:
            return False
        return True
        '''
        # TODO: Check implementation for 2G
        return True

    def setLogicalChannel(self, channel):
        global logicalChannel
        logicalChannel = channel
        self.logicalChannel = channel

    def setSrvCtrlId(self, simId):
        self.srvId = simId

    def getSrvCtr(self):
        return self.router.getCardDictFromId(self.srvId)[sim_router.CTRL_INTERFACE]

    def sendApdu(self, apdu, channel=None, mode=1): #TODO: why can't be used sim_router.INJECT_WITH_FORWARD
        cla = int(apdu[0:2], 16)
        if cla & 0xF0:
            cla = cla & 0xF0
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
            logicalChannel = self.logicalChannel
        if logicalChannel and not cla & 0x0F:
            cla = cla | (self.logicalChannel & 0x0F)
            apdu = "%02X%s" %(int(cla), apdu[2:])
        rapdu = self.router.injectApdu(apdu, self.getSrvCtr(), mode=mode)
        return types.sw1(rapdu), types.sw2(rapdu), types.responseData(rapdu)

    def getDfGsmResponse(self):
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("A0A40000023F00")
        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.sendApdu("A0A40000027F20")
        length = sw2
        #GET_RESPONSE
        sw1, sw2, data = self.getResponse(length)
        return data

    def pin1Enabled(self):
        data = self.getDfGsmResponse()
        #Byte 14 - File characteristics
        #b8=0: CHV1 enabled; b8=1: CHV1 disabled
        #TODO parse TLV
        enabled = not (data[13] & 0b10000000)
        return enabled

    def pin1Status(self):
        data = self.getDfGsmResponse()
        #Byte 19 CHV1 status
        #b0-4 Number of false presentations remaining
        attemptsLeft = data[18] & 0b00001111
        return attemptsLeft

    def pin1UnblockStatus(self):
        data = self.getDfGsmResponse()
        #Byte 20 CHV1 UNBLOCK status
        #b0-4 Number of false presentations remaining
        attemptsLeft = data[19] & 0b00001111
        return attemptsLeft

    def pin2Status(self):
        data = self.getDfGsmResponse()
        #Byte 21 CHV2 status
        #b0-4 Number of false presentations remaining
        attemptsLeft = data[20] & 0b00001111
        return attemptsLeft

    def pin2UnblockStatus(self):
        data = self.getDfGsmResponse()
        #Byte 22 CHV1 UNBLOCK status
        #b0-4 Number of false presentations remaining
        attemptsLeft = data[21] & 0b00001111
        return attemptsLeft

    def admStatus(self, admId):
        admHexStr = {sim_codes.ADM_1 : '0A', sim_codes.ADM_2 : '0B', sim_codes.ADM_3: '0C', sim_codes.ADM_4 : '0D'}
        #VERIFY
        #sw1, sw2, data = self.sendApdu("002000%s00" %admHexStr[admId])
        #if sw1 != 0x63:
        #    return None
        #attemptsLeft = sw2 & 0x0F
        if self.getSrvCtr().mode == sim_reader.MODE_SIM_SOFT:
            attemptsLeft = 3
        else:
            attemptsLeft = 1
        logging.warning("dummy attemps left:%d" %attemptsLeft)
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
        sw1, sw2, data = self.sendApdu("A0C00000%02X" %length)
        if not types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            #fileDescriptor = types.parseFcpTlv(data, types_g.selectTag.FILE_DESCRIPTOR)
            #fileType = fileDescriptor[0]
            type = data[6]
            if type == types.FILE_TYPE_EF:
                fileType = types_g.fileDescriptor.INTERNAL_EF
            else:
                fileType = types_g.fileDescriptor.DF_OR_ADF
            self.setCurrentFileType(fileType)
        return sw1, sw2, data

    def selectMf(self):
        #SELECT_FILE MF
        sw1, sw2, data = self.sendApdu("A0A40000023F00")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G')
        return sw1, sw2, data

    def selectDfGsm(self):
        self.selectMf()
        #SELECT_FILE DF_GSM
        sw1, sw2, data = self.sendApdu("A0A40000027F20")
        types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G')
        return sw1, sw2, data

    def selectFile(self, fid):
        #SELECT_FILE
        sw1, sw2, data = self.sendApdu("A0A4000002%s" %fid)
        if not types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', log=False):
            self.appendCurrentDir(fid)
        return sw1, sw2, data

    def selectFileGsm(self, fid):
        self.selectDfGsm()
        return self.selectFile(fid)

    def writeCurrentFileBinary(self, respData, value):
        fileLength = self.getFileLengthStatus(respData)
        value = types.addTrailingBytes(value, 0xFF, fileLength)
        length = len(value)/2
        sw1, sw2, data = self.sendApdu("A0D60000%02X%s" %(length, value))
        types.assertSw(sw1, sw2, 'NO_ERROR')
        return sw1, sw2, data

    def writeFileBinary(self, fid, value):
        sw1, sw2, respData = self.selectFileGsm(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
            return False

        sw1, sw2, data = self.writeCurrentFileBinary(respData, value)
        if types.assertSw(sw1, sw2, 'NO_ERROR'):
            return False
        return True

    def pin1Verified(self):
        sw1, sw2, data = self.selectFileGsm("6F07")
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
            return None
        sw1, sw2, data = self.getResponse(sw2)
        if not data:
            return sw1, sw2, data

        sw1, sw2, data = self.readCurrentFileBinary(data)
        if not data:
            return False
        else:
            return True

    def getImsiCache(self):
        return self.getSrvCtr().imsi

    def setImsi(self, imsi):
        if len(imsi) % 2:
            dataLow = 9
        else:
            dataLow = 1
        firstByte = dataLow<<4 | int(imsi[0], 16)
        imsi = "%02X%s" %(firstByte, imsi[1:])
        imsi = hextools.encode_BCD(imsi)
        imsi = "08%s" %hextools.bytes2hex(imsi)
        return self.writeFileBinary("6F07", imsi)

    def getAd(self):
        self.selectDfGsm()
        sw1, sw2, data = self.readFileBinary("6FAD")
        return data

    def setAd(self, admData):
        self.selectDfGsm()
        return self.writeFileBinary("6FAD", admData)

    def verifyCode(self, pinId, code=None):
        verify = types_g.iso7816.VERIFY_PIN
        newCode = ""
        length = 0x08
        if pinId == sim_codes.PIN_1:
            chvP2 = types_g.verifyChvP2_2g.chv1
        elif pinId == sim_codes.PIN_1_UNBLOCK:
            chvP2 = types_g.verifyChvUnblockP2.chv1
            verify = types_g.iso7816.UNBLOCK_PIN
            length = 0x10
            newCode = sim_codes.defaultCard[sim_codes.PIN_1]
            newCode = types.addTrailingBytes(newCode.encode("hex"), 0xFF, 8)
        elif pinId == sim_codes.PIN_1_ENABLE:
            chvP2 = types_g.verifyChvP2_2g.chv1
            verify = types_g.iso7816.ENABLE_PIN
        elif pinId == sim_codes.PIN_1_DISABLE:
            chvP2 = types_g.verifyChvP2_2g.chv1
            verify = types_g.iso7816.DISABLE_PIN
        elif pinId == sim_codes.PIN_2:
            chvP2 = types_g.verifyChvP2_2g.chv2
        elif pinId == sim_codes.PIN_2_UNBLOCK:
            chvP2 = types_g.verifyChvUnblockP2.chv2
            verify = types_g.iso7816.UNBLOCK_PIN
            length = 0x10
            newCode = sim_codes.defaultCard[sim_codes.PIN_2]
            newCode = types.addTrailingBytes(newCode.encode("hex"), 0xFF, 8)
        elif pinId == sim_codes.ADM_1:
            chvP2 = types_g.verifyChvP2_2g.adm1
        elif pinId == sim_codes.ADM_4:
            chvP2 = types_g.verifyChvP2_2g.adm4
        else:
            raise Exception("PinId: %02X invalid" %pinId)


        if not code:
            code = sim_codes.defaultCard[pinId]
        #VERIFY
        code = types.addTrailingBytes(code.encode("hex"), 0xFF, 8)
        sw1, sw2, data = self.sendApdu("A0%02X00%02X%02X%s%s" %(verify, chvP2, length, code, newCode))
        sw1Name, swName = types.swName(sw1, sw2)
        if swName == 'NO_ERROR' or sw1 == types_g.sw1.NO_ERROR_PROACTIVE_DATA:
            return True
        elif swName == 'GSM_ACCESS_CONDITION_NOT_FULFILLED':
            logging.error("Verify failed!")
        elif swName == 'GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION':
            logging.error("Verify failed! Attempts left: 0")
        elif swName == 'GSM_CHV_ALREADY_VALIDATED':
            logging.warning("Code invalidated - not enabled")
            return True
        else:
            logging.error("SW:'%s' not expected" %swName)
        return False

    def openChannel(self, originChannel, targetChannel):
        #OPEN_CHANNEL
        length = 0
        if targetChannel == 0:
            length = 1 #  returns the number of assigned channel
        sw1, sw2, data = self.sendApdu("A%01X7000%02X%02X" %(originChannel, targetChannel, length))
        if types.assertSw(sw1, sw2, 'NO_ERROR'):
            return False
        if length:
            return data[0]
        else:
            return targetChannel

    def closeChannel(self, originChannel, targetChannel):
        #CLOSE_CHANNEL
        sw1, sw2, data = self.sendApdu("A%01X7080%02X00" %(originChannel, targetChannel))
        if types.assertSw(sw1, sw2, 'NO_ERROR'):
            return False
        return True

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

    def readCurrentFileBinary(self, data):
        #READ BINARY
        length = self.getFileLengthStatus(data)
        sw1, sw2, data = self.sendApdu("A0B000%04X" %length)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def readFileBinary(self, fid):
        sw1, sw2, data = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
            return sw1, sw2, data

        sw1, sw2, data = self.getResponse(sw2)
        if not data:
            return sw1, sw2, data
        sw1, sw2, data = self.readCurrentFileBinary(data)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def getFileStructure(self, data):
        fileStruct = data[13]
        return fileStruct

    def getRecordStatus(self, data):
        if data[12] == 0:
            logging.error("File structure is not record based, subsequent data length is 0")
            return None, None
        if self.getFileStructure(data) == types.FILE_STRUCTURE_TRANSPARENT:
            logging.error("Selected file is transparent, expecting record based")
            return None, None
        recordLength = data[14]
        nbrOfRecords = self.getFileLengthStatus(data) / recordLength
        return recordLength, nbrOfRecords

    def getFileLengthStatus(self, data):
        length = data[2] << 8 | data[3]
        return length

    def readCurrentFileRecord(self, data, recordId):
        recordLength, nbrOfRecords = self.getRecordStatus(data)
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
            sw1, sw2, data = self.sendApdu("A0B2%02X04%02X" %(id, recordLength))
            dataRecord.extend([data])
            if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                break
        return sw1, sw2, dataRecord

    def readFileRecord(self, fid, recordId=0xFF):
        sw1, sw2, data = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
            return sw1, sw2, data

        sw1, sw2, data = self.getResponse(sw2)
        if not data:
            return sw1, sw2, data

        sw1, sw2, data = self.readCurrentFileRecord(data, recordId)
        types.assertSw(sw1, sw2, checkSw='NO_ERROR')
        return sw1, sw2, data

    def getAccessConditions(self, data, accessMode):
        readUpdate = data[8]
        updateCondition = readUpdate & 0x0F
        readCondition = readUpdate >> 4

        if accessMode == types.AM_EF_UPDATE:
            condition = updateCondition
        elif accessMode == types.AM_EF_READ:
            condition = readCondition
        else:
            logging.error("Unknown access mode: %d" %accessMode)
            return None, None
        conditions = [condition]
        return conditions, None

    def getConditions(self, fid, accessMode):
        sw1, sw2, data = self.selectFileByPath(fid)
        if not data:
            logging.error("Failed to select: %s" %fid)
            return [types.AC_UNKNOWN], None
        conditions, mode = self.getAccessConditions(data, accessMode)
        return conditions, mode

    def getWriteConditions(self, fid):
        return self.getConditions(fid, types.AM_EF_UPDATE)

    def getReadConditions(self, fid):
        return self.getConditions(fid, types.AM_EF_READ)

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
        self.decrementCurrentDir()
        return sw1, sw2, data

    def selectFileByPath(self, absPath):
        sw2 = None
        if not absPath or absPath[0] != "/":
            raise Exception("Invalid path format")

        path = absPath
        # Normalize paths
        if not path.startswith("/3F00"):
            path = "/3F00" + path
        path = path.rstrip("/")
        currDirPath = self.getCurrentDirPath().rstrip("/")
        if not currDirPath.startswith("/3F00"):
            currDirPath = "/3F00" + currDirPath

        parentDirPath = types.parentDirFromPath(path)
        if path == currDirPath:
            # Select the current file.
            path = types.fidFromPath(path)
        elif path.find(currDirPath) == 0:
            # The path to select contains the current path (move forward).
            path = path[len(currDirPath):]
        elif currDirPath.find(parentDirPath) == 0:
            # The current path contains the path to select (move backward).
            fid = types.fidFromPath(absPath)
            fidDir = types.fidFromPath(parentDirPath)
            tmp = currDirPath[len(parentDirPath):]
            currDirFiles = types.getFilesFromPath(currDirPath)
            diffNumOfLevels = len(types.getFilesFromPath(tmp))
            pathNumOfLevels = len(types.getFilesFromPath(parentDirPath))
            if currDirFiles[pathNumOfLevels] == fid:
                diffNumOfLevels -= 1
                pathNumOfLevels += 1
            # Check if it is faster to move backwards,
            # otherwise leave the path unchanged (move forward).
            if pathNumOfLevels >= diffNumOfLevels:
                path = ""
                idx = len(currDirFiles) - 1
                for i in range(diffNumOfLevels):
                    path += "../"
                    idx -= 1
                    if currDirFiles[idx] in [fid, fidDir]:
                        if fid != currDirFiles[idx]:
                            path += fid # add EF name
                        break

        for _file in types.getFilesFromPath(path):
            fileFormat = types.getFileNameFormat(_file)
            if fileFormat == types.FILE_FORMAT_ID:
                sw1, sw2, data = self.selectFile(_file)
                if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
                    return sw1, sw2, []
                #update current dir type based on response
                sw1, sw2, data = self.getResponse(sw2)
            elif fileFormat == types.FILE_FORMAT_DF_PARENT:
                sw1, sw2, data = self.selectParentDir()
                if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G', log=False) and \
                    types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                    return None, None, []
                if not data:
                    sw1, sw2, data = self.getResponse(sw2)
            elif fileFormat == types.FILE_FORMAT_DF_CURRENT:
                pass
            else:
                raise Exception("Format:%d not expected" %fileFormat)
        return sw1, sw2, data

    def listFiles(self):
        path = self.getCurrentDirPath()
        if path == "/":
            path = "3F00"
        path += "/"
        fidCurrentDir =  types.fidFromPath(path)
        formatCurrentDir = types.getFileNameFormat(fidCurrentDir)
        '''
        if formatCurrentDir == types.FILE_FORMAT_ADF_ID:
            fidCurrentDir = "7FFF" #current aid
        '''
        filesToCheck = self.simFiles.findAllChildFiles(path)
        files = []
        for file in filesToCheck:
            fid =  types.fidFromPath(file)
            format = types.getFileNameFormat(file)
            '''
            if format == types.FILE_FORMAT_ADF_NAME:
                fid = self.simFiles.getAdfId(fid)
                if fid:
                    files.append(file)
                #no update of current dir is needed. Just continue
                continue
            '''
            sw1, sw2, data = self.selectFile(fid)
            #if sw1 != types_g.sw1.RESPONSE_DATA_AVAILABLE_3G:
            if sw1 != types_g.sw1.RESPONSE_DATA_AVAILABLE_2G:
                continue
            files.append(file)
            sw1, sw2, data = self.selectFile(fidCurrentDir)
            #if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_3G'):
            if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
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

    def writeCurrentFileRecord(self, data, records, recordId):
        recordLength, nbrOfRecords = self.getRecordStatus(data)
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
            sw1, sw2, data = self.sendApdu("A0DC%02X04%02X%s" %(id, recordLength, record))
            if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                break
            i += 1
        return sw1, sw2, data

    def writeFileRecord(self, fid, value, recordId=0xFF):
        sw1, sw2, data = self.selectFile(fid)
        if types.assertSw(sw1, sw2, checkSw1='RESPONSE_DATA_AVAILABLE_2G'):
            return False
        sw1, sw2, data = self.getResponse(sw2)
        sw1, sw2, data = self.writeCurrentFileRecord(data, value, recordId)
        if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
            return False
        return True
