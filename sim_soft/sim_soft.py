#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Szymon Mielczarek
# (c) 2014 Kamil Wartanowicz

import logging

import sim_xml

from util import types_g
from util import types
from util import hextools
from sim import sim_codes
import sim_auth

class LogicalChannel:
    isOpen = False
    currentDir = "./mf"
    currentFile = None
    currentAdf = None
    currentRecord = None

class SimHandler(object):
    def __init__(self, simXml, satCtrl, simType):
        # Create available channels
        self.logicalChannel = []
        self.simType = simType
        for i in range(types.MAX_LOGICAL_CHANNELS):
            channel = LogicalChannel()
            self.logicalChannel.append(channel)

        # Logical channel 0 (basic) is always open
        self.currentChannel = self.logicalChannel[0]
        self.currentChannel.isOpen = True

        self.simXml = simXml
        self.satCtrl = satCtrl
        self.responseData = []

    def isChannelOpen(self, chId):
        return self.logicalChannel[chId].isOpen

    def setChannel(self, chId):
        self.currentChannel = self.logicalChannel[chId]

    def getChannel(self, chId):
        return self.logicalChannel[chId]

    # Response for MF, DF, or ADF with FCP template (ETSI TS 102 221 V8.2.0)
    def createResponseDf_3g(self, file):
        fcpData = []
        tlvData = []

        # File Descriptor
        ## File descriptor byte
        tlvData.append(types_g.fileDescriptor.DF_OR_ADF | types_g.fileDescriptor.SHAREABLE)
        ## Data coding byte (hardcoded)
        tlvData.append(0x21)
        types.addTlv(fcpData, types_g.selectTag.FILE_DESCRIPTOR, tlvData)

        # File Identfifier (e.g. 0x3F00) (optional for ADF, else mandatory)
        fidStr = self.simXml.getFileId(file)
        fileId = int(fidStr, 16)
        isAdf = types.isFidAdf(fidStr)
        if not isAdf:
            tlvData = []
            tlvData.append(fileId >> 8)
            tlvData.append(fileId & 0x00FF)
            types.addTlv(fcpData, types_g.selectTag.FILE_IDENTIFIER, tlvData)
        else:
            # DF name (AID) (mandatory for only ADF)
            aid = self.simXml.getFileAid(file)
            types.addTlv(fcpData, types_g.selectTag.DF_NAME, sim_xml.xmlValueToBytes(aid))

        # Properietary information  (mandatory for only MF)
        if fileId == 0x3F00:
            tlvData = []
            ## UICC characteristics (mandatory for MF)
            tlv2Data = []
            tlv2Data.append(0x71) # clock stop allowed, no preferred level, support A,B and C of Supply voltage class
            types.addTlv(tlvData, types_g.properietaryTag.UICC_CHARACTERISTICS, tlv2Data)
            ## Application power consumption (is optional for ADFs, not applicable for others)
            ## Minimum application power consumption (is optional for ADFs, not applicable for others)
            ## Amount of available memory (mandatory only for structured EFs, optional for ADF, MF, DF)
            tlv2Data = []
            tlv2Data.append(0xC2) # hardcoded
            tlv2Data.append(0x07)
            types.addTlv(tlvData, types_g.properietaryTag.AMOUNT_OF_AVAIL_MEMORY, tlv2Data)
            ## File details (mandatory only for structured EFs)
            ## Reserved file size (present only for structured EFs, for which it is mandatory)
            ## Maximum file size (present only for structured EFs, for which it is optional)
            ## Supported system commands (if supported is mandatory for the MF and optional for DFs)
            ## Specific UICC environmental conditions (if supported shall be present for the MF)

            types.addTlv(fcpData, types_g.selectTag.PROPRIETARY_INF, tlvData)

        # Life Cycle Status Integer
        status = [types.LIFE_CYCLE_STATE_OPER_ACTIVATED]
        types.addTlv(fcpData, types_g.selectTag.LIFE_CYCLE_STATUS, status)

        # Security attributes (exactly one should be present)
        ## Referenced to expanded format
        arrFidStr, arrRule = self.simXml.findEfArr(file)
        arrId = int(arrFidStr, 16)
        tlvData = []
        tlvData.append(arrId >> 8)     # EFarr File ID - High
        tlvData.append(arrId & 0x00FF) # EFarr File ID - Low
        tlvData.append(arrRule) # EFarr Record number
        #data.append(0x00) # AM byte
        #data.append(0x00) # SC bytes
        types.addTlv(fcpData, types_g.selectTag.SECURITY_ATRIBUTES_COMPACT, tlvData)

        # PIN Status Templete DO
        tlvData = []
        ## Status of the PIN(s) enabled/disabled
        pinEnabled = self.simXml.enabledChv("chv1")
        if pinEnabled:
            pinStatus = 0x80 # only the first key reference indicated
        else:
            pinStatus = 0x00
        types.addTlv(tlvData, types_g.pinStatusTag.PIN_STATUS, [pinStatus])
        ## Usage qualifier (mandatory for universal PIN)
        types.addTlv(tlvData, types_g.pinStatusTag.USAGE_QUALIFIER, [types.PIN_VERIFY]) # user PIN veryfication
        ## Key references (for each bit set to '1' in PIN_STATUS)
        keys = [types.KEY_REF_PIN1]
        types.addTlv(tlvData, types_g.pinStatusTag.KEY_REFERENCE, keys)
        if isAdf:
            #add pin2 reference otherwise FDN does not work
            keys = [types.KEY_REF_PIN2]
            types.addTlv(tlvData, types_g.pinStatusTag.KEY_REFERENCE, keys)
            types.addTlv(fcpData, types_g.selectTag.PIN_STATUS_TEMPLATE, tlvData)

        # Total file size (optional)
        #types.addTlv(data, types_g.selectTag.TOTAL_FILE_SIZE, ??)

        # File Control Parameters (FCP) template of the selected file
        data = []
        types.addTlv(data, types_g.selectTag.FCP, fcpData)

        return data

    # Response for an EF with FCP template
    def createResponseEf_3g(self, file):
        fcpData = []
        tlvData = []

        # File Descriptor
        ## File descriptor byte
        struct = self.simXml.getFileStruct(file)
        if struct == types.FILE_STRUCTURE_TRANSPARENT:
            efType = types_g.fileDescriptor.TRANSPARENT_STRUCTURE
        elif struct == types.FILE_STRUCTURE_LINEAR_FIXED:
            efType = types_g.fileDescriptor.LINEAR_FIXED_STRUCTURE
        elif struct == types.FILE_STRUCTURE_CYCLIC:
            efType = types_g.fileDescriptor.CYCLIC_STRUCTURE
        else:
            efType = types_g.fileDescriptor.NO_INFORMATION_GIVEN
        tlvData.append(efType | types_g.fileDescriptor.SHAREABLE)
        ## Data coding byte
        tlvData.append(0x21) # hardcoded
        if struct in [types.FILE_STRUCTURE_LINEAR_FIXED, types.FILE_STRUCTURE_CYCLIC]:
            ## Record length (2 bytes - mandatory for linear fixed and cyclic files)
            recordLength = 0
            recordLength = self.simXml.getFileRecordLength(file)
            tlvData.append(recordLength >> 8)
            tlvData.append(recordLength & 0x00FF)
            ## Number of records
            size = self.simXml.getFileSize(file)
            tlvData.append(size/recordLength)
        types.addTlv(fcpData, types_g.selectTag.FILE_DESCRIPTOR, tlvData)

        # File Identfifier (e.g. 0x3F00) (optional for ADF, else mandatory)
        fileId = int(self.simXml.getFileId(file), 16)
        tlvData = []
        tlvData.append(fileId >> 8)
        tlvData.append(fileId & 0x00FF)
        types.addTlv(fcpData, types_g.selectTag.FILE_IDENTIFIER, tlvData)

        # Properietary information (mandatory for only MF)
        tlvData = []
        #if fileId == 0x3F00:
        ## UICC characteristics (mandatory for MF)
        tlv2Data = []
        tlv2Data.append(0x71) # clock stop allowed, no preferred level, support A,B and C of Supply voltage class
        types.addTlv(tlvData, types_g.properietaryTag.UICC_CHARACTERISTICS, tlv2Data)
        ## Application power consumption (is optional for ADFs, not applicable for others)
        ## Minimum application power consumption (is optional for ADFs, not applicable for others)
        ## Amount of available memory (mandatory only for structured EFs, optional for ADF, MF, DF)
        ## File details (mandatory only for structured EFs)
        ## Reserved file size (present only for structured EFs, for which it is mandatory)
        ## Maximum file size (present only for structured EFs, for which it is optional)
        ## Supported system commands (if supported is mandatory for the MF and optional for DFs)
        ## Specific UICC environmental conditions (if supported shall be present for the MF)

        types.addTlv(fcpData, types_g.selectTag.PROPRIETARY_INF, tlvData)

        # Life Cycle Status Integer
        status = [types.LIFE_CYCLE_STATE_OPER_ACTIVATED]
        types.addTlv(fcpData, types_g.selectTag.LIFE_CYCLE_STATUS, status)

        # Security attributes (exactly one should be present)
        ## Referenced to expanded format
        arrFidStr, arrRule = self.simXml.findEfArr(file)
        arrId = int(arrFidStr, 16)
        tlvData = []
        tlvData.append(arrId >> 8)     # EFarr File ID
        tlvData.append(arrId & 0x00FF) # EFarr File ID
        tlvData.append(arrRule) # EFarr Record number
        #data.append(0x00) # AM byte
        #data.append(0x00) # SC bytes
        types.addTlv(fcpData, types_g.selectTag.SECURITY_ATRIBUTES_COMPACT, tlvData)

        # File size (mandatory)
        size = self.simXml.getFileSize(file)
        tlvData = []
        tlvData.append(size >> 8)
        tlvData.append(size & 0x00FF)
        types.addTlv(fcpData, types_g.selectTag.FILE_SIZE, tlvData)

        # Total file size (optional)
        #types.addTlv(fcpData, types_g.selectTag.TOTAL_FILE_SIZE, ??)

        # Short File Identifier (optional)
        #types.addTlv(fcpData, types_g.selectTag.SHORT_FILE_IDENTIFIER, ??)

        # File Control Parameters (FCP) template of the selected file
        data = []
        types.addTlv(data, types_g.selectTag.FCP, fcpData)

        return data

    def createResponseDf_2g(self, file):
        data = []
        #1-2 RFU
        data.append(0x00)
        data.append(0x00)
        #3-4 memory of the selected directory...
        data.append(0x00)
        data.append(0x00)
        #5-6 fileID
        fileId = int(self.simXml.getFileId(file), 16)
        data.append(fileId >> 8)
        data.append(fileId & 0x00FF)
        #7 type of file
        type = self.simXml.getFileType(file)
        data.append(type)
        #8-12 RFU
        data.append(0x00)
        data.append(0x00)
        data.append(0x00)
        data.append(0x00)
        data.append(0x00)
        #13 Length of the following data (byte 14 to the end)
        #will be updated on the end - 13th byte
        data.append(0x00)
        #14 File characteristics
        #b8=0: CHV1 enabled; b8=1: CHV1 disabled
        chvEnabled = (not self.simXml.enabledChv("chv1")) << 7
        characteristic = 0x33 #hardcoded
        characteristic |= chvEnabled
        data.append(characteristic)
        #15 Number of DF inside
        nbrOfChild = self.simXml.countChildDf(self.currentChannel.currentDir)
        data.append(nbrOfChild)
        #16 Number of EF inside
        nbrOfChild = self.simXml.countChildEf(self.currentChannel.currentDir)
        data.append(nbrOfChild)
        #17 Number of CHVs, UNBLOCK CHVs and administrative codes
        nbrOfChild = self.simXml.getNumberOfChv()
        data.append(nbrOfChild)
        #18 RFU
        data.append(0x00)
        #19 CHV1 status
        #b0-4 Number of false presentations remaining
        #b8=1 secret code initialised
        status = 0b10000000
        status |= self.simXml.remaningAttemptsChv("chv1")
        data.append(status)
        #20 CHV1 UNBLOCK status
        #b0-4 Number of false presentations remaining
        #b8=1 secret code initialised
        status = 0b10000000
        status |= self.simXml.remaningAttemptsChv("chv1_unblock")
        data.append(status)
        #21 CHV2 status
        #b0-4 Number of false presentations remaining
        #b8=1 secret code initialised
        status = 0b10000000
        status |= self.simXml.remaningAttemptsChv("chv2")
        data.append(status)
        #22 CHV2 UNBLOCK status
        #b0-4 Number of false presentations remaining
        #b8=1 secret code initialised
        status = 0b10000000
        status |= self.simXml.remaningAttemptsChv("chv2_unblock")
        data.append(status)
        #add 00010000CDB700000000?

        #update length - 13th byte
        data[12] = len(data[13:])
        return data

    def createResponseEf_2g(self, file):
        data = []
        #1-2 RFU
        data.append(0x00)
        data.append(0x00)
        #3-4 File size
        size = self.simXml.getFileSize(file)
        data.append(size >> 8)
        data.append(size & 0x00FF)
        #5-6 fileID
        fileId = int(self.simXml.getFileId(file), 16)
        data.append(fileId >> 8)
        data.append(fileId & 0x00FF)
        #7 type of file
        type = self.simXml.getFileType(file)
        data.append(type)
        #8 RFU
        #For a cyclic EF all bits except bit 7 are RFU; b7=1 indicates that the INCREASE command is allowed
        #todo: implement
        data.append(0x00)
        #9-11 Access conditions
        #  0 ALWays
        #  1 CHV1
        #  2 CHV2
        #  3 Reserved for GSM Future Use
        #  4-14 ADM1-ADM10
        #  F NEVer
        #9 b1-4 Update, b5-8 Read/Seek
        updateCondition = self.getAccessCondition(file, types.AM_EF_UPDATE)
        readCondition = self.getAccessCondition(file, types.AM_EF_READ)
        data.append(updateCondition | (readCondition <<4))
        #10 b1-4 RFU, b5-8 Increase
        increaseCondition = self.getAccessCondition(file, types.AM_EF_INCREASE)
        data.append(increaseCondition << 4)
        #11 b1-4 Invalidate, b5-8 Rehabilitate
        invalidateCondition = self.getAccessCondition(file, types.AM_EF_DEACTIVATE)
        rehabilitateCondition = self.getAccessCondition(file, types.AM_EF_ACTIVATE)
        data.append(invalidateCondition | (rehabilitateCondition <<4))
        #12  File status
        #   b1=0: invalidated; b1=1: not invalidated
        #   b2 RFU
        #   b3=0: not readable or updatable when invalidated
        #   b3=1: readable and updatable when invalidated
        #   b5-8 RFU
        fileStatus = self.getFileStatus(file)
        data.append(fileStatus)
        #13 Length of the following data (byte 14 to the end)
        data.append(0x02)
        #14 Structure of EF
        struct = self.simXml.getFileStruct(file)
        data.append(struct)
        #15 Length of a record
        if struct == types.FILE_STRUCTURE_TRANSPARENT:
            recordLength = 0
        else:
            recordLength = self.simXml.getFileRecordLength(file)
        data.append(recordLength)
        return data

    def getResponse(self, apdu):
        data = self.responseData
        sw = self.swNoError()
        return data, sw

    def getFileStatus(self, file):
        invalidated = not int(file.find("invalidated").text)
        invalidatedRw = int(file.find("rw_invalidated").text)
        status = invalidated | (invalidatedRw << 2)
        return status

    def swNoError(self):
        return self.satCtrl.swNoError()

    def isCurrentDirOnMf(self):
        if self.currentChannel.currentDir in ("./mf", "./mf[@id='3F00']"):
            return True
        else:
            return False

    def selectByFileId(self, fid):
        #SELECT by File IDentifier referencing (ETSI TS 102 221 p.8.4.1)
        fidStr = "%.4X" % fid
        if fidStr == '7FFF':
            # the ADF of the current active application
            file = self.simXml.findFile(self.currentChannel.currentAdf)
        else:
            if fidStr == '0000':
                logging.warning("fileId is empty, check the implementation")
            # any file which is an immediate child of the current DF
            file = self.simXml.findFileInDir(self.currentChannel.currentDir, fidStr)
            if file == None and not self.isCurrentDirOnMf():
                # the parent DF of the current DF
                parentPath = types.parentDirFromPath(self.currentChannel.currentDir)
                file = self.simXml.findFile(parentPath)
                if self.simXml.getFileId(file) != fidStr:
                    file = None
                if file == None:
                    # any DF which is an immediate child of the parent of the current DF
                    file = self.simXml.findFileInDir(parentPath, fidStr)
                    if file != None:
                        if self.simXml.getFileType(file) == types.FILE_TYPE_EF:
                            file = None # only DFs
        return file

    def selectParentDf(self):
        if not self.isCurrentDirOnMf():
            path = types.parentDirFromPath(self.currentChannel.currentDir)
        else:
            path = self.currentChannel.currentDir # MF
        return self.simXml.findFile(path)

    def selectByDfName(self, aid):
        return self.simXml.findAdf(aid)

    def selectByPathFromBase(self, base, pathToSelect):
        i = 0
        pathLen = len(pathToSelect)
        while i < pathLen:
            fidStr = "%s" %pathToSelect[i:i+4]
            if fidStr == '7FFF':
                path = self.currentChannel.currentAdf
                file = self.simXml.findFile(path)
            else:
                file = self.simXml.findFileInDir(base, fidStr)
                path = self.simXml.getPathFromFile(file)
            if file == None:
                break
            base = path
            i += 4
        return file

    def selectByPathFromMf(self, pathToSelect):
        return self.selectByPathFromBase("./mf[@id='3F00']", pathToSelect)

    def selectByPathFromDf(self, pathToSelect):
        return self.selectByPathFromBase(self.currentChannel.currentDir, pathToSelect)

    def select(self, apdu):
        data = []
        file = None
        returnData = True

        if self.simType == types.TYPE_SIM and types.p2(apdu):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        selectType = types.p1(apdu)
        returnType = types.returnType(apdu) # p2
        appControl = types.appControl(apdu) # p2
        dataLcLength = types.p3(apdu)
        if not dataLcLength:
            dataLcLength = 0
            dataLc = None
        else:
            dataLc = types.dataLc(apdu)
        wrongLc = False

        if selectType == types.SELECT_DF_EF_MF:
            if dataLcLength != 2:
                wrongLc = True
            file = self.selectByFileId(types.fileId(apdu))
        elif selectType == types.SELECT_CHILD_DF:
            raise Exception("Selecting child DF is not implemented")
        elif selectType == types.SELECT_PARRENT_DF:
            if dataLcLength != 0:
                wrongLc = True
            file = self.selectParentDf()
        elif selectType == types.SELECT_BY_DF_NAME:
            #  Selection by AID
            # TODO: handle app activation and termination.
            if not 1 <= dataLcLength <= 16:
                wrongLc = True
            file = self.selectByDfName(types.aid(apdu))
        elif selectType == types.SELECT_BY_PATH_FROM_MF:
            if not 2 <= dataLcLength <= 10 or dataLcLength % 2:
                wrongLc = True
            pathToSelect = hextools.bytes2hex(dataLc)
            file = self.selectByPathFromMf(pathToSelect)
        elif selectType == types.SELECT_BY_PATH_FROM_DF:
            if not 2 <= dataLcLength <= 10 or dataLcLength % 2:
                wrongLc = True
            pathToSelect = hextools.bytes2hex(dataLc)
            file = self.selectByPathFromDf(pathToSelect)
        else:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        if wrongLc or (dataLc and len(dataLc) != dataLcLength):
            sw = types_g.sw.WRONG_LENGTH
            return data, sw

        if appControl not in (types.SELECT_APP_ACTIVATION,
                              types.SELECT_APP_TERMINATION):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        if returnType == types.SELECT_NO_DATA_RETURNED:
            if selectType == types.SELECT_DF_EF_MF and not types.dataLc(apdu):
                self.currentChannel.currentDir = "./mf"
                self.currentChannel.currentFile = None
                sw = types_g.sw.NO_ERROR
                return data, sw  # No data returned
            else:
                returnData = False
        elif returnType != types.SELECT_RETURN_FCP_TEMPLATE and \
             self.simType != types.TYPE_SIM:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        if file == None:
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        filePath = self.simXml.getPathFromFile(file)

        if self.simXml.getFileType(file) == types.FILE_TYPE_EF:
            self.currentChannel.currentFile = filePath
            fileDirPath = self.simXml.getParentDir(filePath)
            self.currentChannel.currentDir = fileDirPath
            self.currentChannel.currentRecord = None
            if not returnData:
                sw = types_g.sw.NO_ERROR
                return data, sw  # No data returned
            if self.simType == types.TYPE_SIM:
                self.responseData = self.createResponseEf_2g(file)
            else:
                self.responseData = self.createResponseEf_3g(file)
        else: # MF or DF
            if selectType == types.SELECT_BY_DF_NAME:
                self.currentChannel.currentAdf = filePath
            self.currentChannel.currentDir = filePath
            self.currentChannel.currentFile = None # not set
            if not returnData:
                sw = types_g.sw.NO_ERROR
                return data, sw  # No data returned
            if self.simType == types.TYPE_SIM:
                self.responseData = self.createResponseDf_2g(file)
            else:
                self.responseData = self.createResponseDf_3g(file)

        if self.simType == types.TYPE_SIM:
            sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_2G
        else:
            sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_3G
        sw2 = len(self.responseData)
        sw = types.packSw(sw1, sw2)
        return data, sw

    def status(self, apdu):
        """
        This function returns information concerning
        the current directory or current application.
        """
        data = []
        p1 = types.p1(apdu)
        p2 = types.p2(apdu)
        p3 = types.p3(apdu) # Le
        if p1 > 2 or p2 > 0x0F:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        returnType =  p2 & 0b00001111
        if returnType == types.STATUS_SELECT_RESPONSE_RETURNED:
            df = self.simXml.findFile(self.currentChannel.currentDir)
            if df == None:
                sw = types_g.sw.TECHNICAL_PROBLEM # DF or EF integrity error
                return data, sw
            if self.simType == types.TYPE_SIM:
                self.responseData = self.createResponseDf_2g(df)
                sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_2G
            else:
                self.responseData = self.createResponseDf_3g(df)
                if p3 not in (None, 0):
                    if p3 == len(self.responseData):
                        sw = self.swNoError()
                        data = self.responseData
                    else:
                        sw = types_g.sw.WRONG_LENGTH
                    return data, sw
                else:
                    sw1 = types_g.sw1.REPEAT_COMMAND_WITH_LE
            sw2 = len(self.responseData)
            sw = types.packSw(sw1, sw2)
        elif returnType == types.STATUS_DF_NAME_RETURNED:
            file = self.simXml.findFile(self.currentChannel.currentAdf)
            if file == None:
                sw = types_g.sw.FILE_NOT_FOUND
                return data, sw
            aid = self.simXml.getFileAid(file)
            aidBytes = sim_xml.xmlValueToBytes(aid)
            self.responseData = [types_g.selectTag.DF_NAME, len(aidBytes)]
            self.responseData.extend(aidBytes)
            if p3 not in (None, 0):
                if p3 == len(self.responseData):
                    sw = self.swNoError()
                    data = self.responseData
                else:
                    sw = types_g.sw.WRONG_LENGTH
                return data, sw
            else:
                sw2 = len(self.responseData)
                sw1 = types_g.sw1.REPEAT_COMMAND_WITH_LE
                sw = types.packSw(sw1, sw2)
        elif returnType == types.STATUS_NO_DATA_RETURNED:
            sw = self.swNoError()
        else:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
        return data, sw

    def verifyCondition(self, condition):
        sw = self.swNoError()
        if condition == types.AC_ALWAYS:
            return sw
        elif condition == types.AC_CHV1:
            return self.checkChv("chv1")
        elif condition == types.AC_CHV2:
            return self.checkChv("chv2")
        elif condition == types.AC_NEVER:
            return types_g.sw.SECURITY_STATUS_NOT_SATISFIED
        else:
            return sw

    def checkAccessCondition(self, file, accessMode):
        sw = self.swNoError()

        conditions, mode = self.getAccessConditionsForFile(file, accessMode)
        for condition in conditions:
            sw = self.verifyCondition(condition)
            if mode == None:
                return sw
            if mode == types.SC_DO_OR_TEMPLATE_TAG:
                if sw == self.swNoError():
                    return sw
            elif mode == types.SC_DO_AND_TEMPLATE_TAG:
                if sw != self.swNoError():
                    return sw
            elif mode == types.SC_DO_NOT_TEMPLATE_TAG:
                if sw == self.swNoError():
                    return sw
        return sw

    def checkFileAndAccessCondition(self, accessMode):
        file = None

        if self.currentChannel.currentFile == None:
            sw = types_g.sw.COMMAND_NOT_ALLOWED_NO_EF_SELECTED
            return sw, file

        file = self.simXml.findFile(self.currentChannel.currentFile)
        if file == None:
            sw = types_g.sw.FILE_NOT_FOUND
            return sw, file

        sw = self.checkAccessCondition(file, accessMode)
        return sw, file

    def checkChv(self, chv):
        sw = self.swNoError()

        if (self.simXml.enabledChv("chv1") and
            not self.simXml.verifiedChv("chv1")):

            if self.simXml.remaningAttemptsChv(chv):
                if self.simType == types.TYPE_SIM:
                    sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
                else:
                    sw = types_g.sw.SECURITY_STATUS_NOT_SATISFIED
            else:
                #PUK needed
                if self.simType == types.TYPE_SIM:
                    sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
                else:
                    sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
        return sw

    def readBinary(self, apdu):
        data = []

        if types.p1(apdu) & types_g.binaryCmdP1.SFI_MODE:
            logging.warning("SFI not implemented")
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        sw, file = self.checkFileAndAccessCondition(types.AM_EF_READ)
        if sw != self.swNoError():
            return data, sw

        fileStruct = self.simXml.getFileStruct(file)
        if fileStruct != types.FILE_STRUCTURE_TRANSPARENT:
            sw = types_g.sw.COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE
            return data, sw

        if not self.simXml.isFileEnabled(file):
            sw = types_g.sw.REFERNCE_DATA_INVALIDATE
            return data, sw

        offset = types.binaryOffset(apdu)
        # p3 -> Le field (number of bytes to be read)
        length = types.p3(apdu)
        if length == 0:
            # All the bytes until the end of the file should be read
            # within the limit of 256 for a short Le field.
            length = self.simXml.getFileSize(file)
            if length > 256:
                length = 256

        data = self.simXml.getBinaryValue(file)
        data = data[offset:length]

        return data, sw

    def updateBinary(self, apdu):
        data = []

        if types.p1(apdu) & types_g.binaryCmdP1.SFI_MODE:
            logging.warning("SFI not implemented")
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        sw, file = self.checkFileAndAccessCondition(types.AM_EF_UPDATE)
        if sw != self.swNoError():
            return data, sw

        fileStruct = self.simXml.getFileStruct(file)
        if fileStruct != types.FILE_STRUCTURE_TRANSPARENT:
            sw = types_g.sw.COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE
            return data, sw

        if not self.simXml.isFileEnabled(file):
            sw = types_g.sw.REFERNCE_DATA_INVALIDATE
            return data, sw

        offset = types.binaryOffset(apdu)
        length = types.p3(apdu)
        value = types.dataLc(apdu)

        if length == None or length != len(value):
            sw = types_g.sw.WRONG_LENGTH
            return data, sw

        data = self.simXml.getBinaryValue(file)
        data[offset : length] = value
        self.simXml.setBinaryValue(file, data)
        data = []
        return data, sw

    def _getFileRecordNumber(self, file, mode, recordId=0):
        recordNo = types.INVALID_RECORD_NUMBER
        numOfRecords = self.simXml.getFileNumberOfRecords(file)
        fileStruct = self.simXml.getFileStruct(file)
        if mode is types_g.readRecordMode.ABSOLUTE_OR_CURRENT:
            if recordId == 0: # "CURRENT_RECORD"
                if not self.currentChannel.currentRecord:
                    sw = types_g.sw.INVALID_DATA_ADDRESS
                    return types.INVALID_RECORD_NUMBER, sw
                recordNo = self.currentChannel.currentRecord
            else: # Absolute mode
                recordNo = recordId
        elif mode is types_g.readRecordMode.NEXT_RECORD:
            recordNo = self.currentChannel.currentRecord
            if recordNo is None:
                recordNo = 1 # set first
            else:
                recordNo += 1
                if recordNo > numOfRecords:
                    if fileStruct == types.FILE_STRUCTURE_CYCLIC:
                        recordNo = 1
                    else:
                        sw = types_g.sw.INVALID_DATA_ADDRESS
                        return types.INVALID_RECORD_NUMBER, sw
            self.currentChannel.currentRecord = recordNo
        elif mode is types_g.readRecordMode.PREVIOUS_RECORD:
            recordNo = self.currentChannel.currentRecord
            if recordNo is None:
                recordNo = numOfRecords # set last
            else:
                recordNo -= 1
                if recordNo <= 0:
                    if fileStruct == types.FILE_STRUCTURE_CYCLIC:
                        recordNo = numOfRecords
                    else:
                        sw = types_g.sw.INVALID_DATA_ADDRESS
                        return types.INVALID_RECORD_NUMBER, sw
            self.currentChannel.currentRecord = recordNo
        else:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return types.INVALID_RECORD_NUMBER, sw

        sw = types_g.sw.NO_ERROR
        return recordNo, sw

    def readRecord(self, apdu):
        data = []

        p1 = types.p1(apdu) # record number
        p2 = types.p2(apdu)

        select = p2 & types_g.readRecordSelect.SFI
        if select != 0:
            logging.warning("SFI not implemented")
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        sw, file = self.checkFileAndAccessCondition(types.AM_EF_READ)
        if sw != self.swNoError():
            return data, sw

        fileStruct = self.simXml.getFileStruct(file)
        if fileStruct == types.FILE_STRUCTURE_TRANSPARENT:
            sw = types_g.sw.COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE
            return data, sw

        if not self.simXml.isFileEnabled(file):
            sw = types_g.sw.REFERNCE_DATA_INVALIDATE
            return data, sw

        mode = p2 & 0b00000111
        recordNo, sw = self._getFileRecordNumber(file, mode, p1)
        if not recordNo:
            return data, sw

        data = self.simXml.getFileRecord(file, recordNo)
        if data == []:
            #e.g. file is transparent
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw
        return data, sw

    def updateRecord(self, apdu):
        data = []

        p1 = types.p1(apdu) # record number
        p2 = types.p2(apdu)

        select = p2 & types_g.readRecordSelect.SFI
        if select != 0:
            logging.warning("SFI not implemented")
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        sw, file = self.checkFileAndAccessCondition(types.AM_EF_UPDATE)
        if sw != self.swNoError():
            return data, sw

        fileStruct = self.simXml.getFileStruct(file)
        if fileStruct == types.FILE_STRUCTURE_TRANSPARENT:
            sw = types_g.sw.COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE
            return data, sw

        if not self.simXml.isFileEnabled(file):
            sw = types_g.sw.REFERNCE_DATA_INVALIDATE
            return data, sw

        mode = p2 & 0b00000111
        recordNo, sw = self._getFileRecordNumber(file, mode, p1)
        if not recordNo:
            return data, sw

        value = types.dataLc(apdu)
        self.simXml.updateFileRecord(file, recordNo, value)
        return data, sw

    def _searchFileRecords(self,
                          file,
                          searchString,
                          startRecord,
                          direction=types_g.fileSearchType.FORWARD_SEARCH_FROM_P1,
                          offsetVal=0,
                          offsetMode=types_g.searchStartMode.START_FROM_OFFSET):
        recordsFound = []

        if direction == types_g.fileSearchType.BACKWARD_SEARCH_FROM_P1:
            start = startRecord
            stop = 0
            step = -1
        else: # forward
            numOfRecords = self.simXml.getFileNumberOfRecords(file)
            start = startRecord
            stop = numOfRecords + 1
            step = 1

        for id in range(start, stop, step):
            record = self.simXml.getFileRecord(file, id)
            if offsetMode == types_g.searchStartMode.START_FROM_VALUE:
                try:
                    # find the first occurence of the character
                    offset = record.index(offsetVal) + 1
                except:
                    continue
            else:
                offset = offsetVal
            # Check if a record contains searched string
            if types.isSublist(searchString, record[offsetVal:]):
                recordsFound.append(id)
        return recordsFound

    def searchRecord(self, apdu):
        """
        This function searches through a linear fixed or cyclic EF
        to find record(s) containing a specific pattern
        """
        data = []

        p1 = types.p1(apdu)
        p2 = types.p2(apdu) # type and search mode
        dataField = types.dataLc(apdu)
        le = types.le(apdu) # empty or maximum length of response data #TODO: handle it

        sw, file = self.checkFileAndAccessCondition(types.AM_EF_READ)
        if sw != self.swNoError():
            return data, sw

        fileStruct = self.simXml.getFileStruct(file)
        if fileStruct == types.FILE_STRUCTURE_TRANSPARENT:
            sw = types_g.sw.COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE
            return data, sw

        if not self.simXml.isFileEnabled(file):
            sw = types_g.sw.REFERNCE_DATA_INVALIDATE
            return data, sw

        recordLength = self.simXml.getFileRecordLength(file)
        fileSize = self.simXml.getFileSize(file)
        numOfRecords = fileSize / recordLength
        recordsFound = []
        recordNo = p1 # record number ('00' indicates: current record)

        if recordNo > numOfRecords:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2 #TODO: check
            return data, sw

        if recordNo == 0:
            if self.currentChannel.currentRecord is None:
                sw = types_g.sw.INVALID_DATA_ADDRESS
                return data, sw
            recordNo = self.currentChannel.currentRecord

        if self.simType == types.TYPE_SIM:
            searchMode = p2 & 0b00000011
            searchType = p2 & 0b00010000
            searchString = dataField
            #todo implement record search
            logging.warning("Searching records is not implemented for 2G SIM")
            recordsFound = 1
            # There are no response parameters/data for a type 1 SEEK
            if searchType == types_g.fileSeekType.TYPE_2:
                sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_2G
                sw2 = recordsFound
                sw = types.packSw(sw1, sw2)
        else: # USIM
            searchType = p2 & 0b00000111
            selectType = p2 & 0b11111000 # '0' indicates current selected EF else SFI
            if selectType != 0:
                raise Exception("SFI not implemented")

            if searchType == types_g.fileSearchType.ENHENCED_SEARCH:
                """
                Search string from a given offset within the records
                or from the first occurrence of a given byte within the records
                """
                # Search indication (2 bytes) followed by search string
                searchIndication = dataField[0:2]
                searchString = dataField[2:]

                if len(searchString) > recordLength:
                    sw = types_g.sw.WRONG_LENGTH #TODO: check
                    return data, sw

                # The second byte the search indication is either an offset (b3=0 in P1) or a value (b3=1 in P1)
                offsetMode = searchIndication[0] & (1<<3) # offse mode
                searchMode = searchIndication[0] & 0b00000111
                offset = searchIndication[1]
                if searchMode == types_g.fileSearchIndication.FORWARD_SEARCH_FROM_P1:
                    recordsFound = self._searchFileRecords(file, searchString, recordNo,
                                                        offsetVal=offset, offsetMode=offsetMode)
                elif searchMode == types_g.fileSearchIndication.BACKWARD_SEARCH_FROM_P1:
                    recordsFound = self._searchFileRecords(file, searchString, recordNo,
                                                         offsetVal=offset, offsetMode=offsetMode,
                                                         direction=types_g.fileSearchType.BACKWARD_SEARCH_FROM_P1)
                elif searchMode == types_g.fileSearchIndication.FORWARD_SEARCH_FROM_NEXT_RECORD:
                    raise Exception("Search mode %02X is not implemented" % searchMode) # requires the record pointer
                elif searchMode == types_g.fileSearchIndication.BACKWARD_SEARCH_FROM_PREVIOUS_RECORD:
                    raise Exception("Search mode %02X is not implemented" % searchMode) # requires the record pointer
            elif searchType == types_g.fileSearchType.PROPERIETARY_SEARCH:
                # Proprietary data
                raise Exception("PROPERIETARY_SEARCH not implemented")
            else: # Simple search
                """ Search string from the first byte of records """
                searchString = dataField
                if len(searchString) > recordLength:
                    sw = types_g.sw.WRONG_LENGTH
                    return data, sw
                searchMode = searchType
                if searchMode == types_g.fileSearchType.FORWARD_SEARCH_FROM_P1:
                    recordsFound = self._searchFileRecords(file, searchString, recordNo)
                elif searchMode == types_g.fileSearchType.BACKWARD_SEARCH_FROM_P1:
                    recordsFound = self._searchFileRecords(file, searchString, recordNo,
                                                        direction=types_g.fileSearchType.BACKWARD_SEARCH_FROM_P1)

        self.responseData = recordsFound
        resultLen = len(self.responseData)
        if resultLen:
            # The record pointer shall be set to the first record
            # where the search pattern was found.
            self.currentChannel.currentRecord = recordsFound[0]
            sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_3G
            sw2 = resultLen
            sw = types.packSw(sw1, sw2)

        return data, sw

    def getFirstFreeChannelNumber(self):
        i = 0
        for channel in self.logicalChannel:
            if channel.isOpen == False:
                return i
            i += 1
        return None

    def manageChannel(self, apdu):
        data = []

        cla = types.cla(apdu)
        p1 = types.p1(apdu)
        p2 = types.p2(apdu)

        # Origin logical channel values are encoded
        # in the two least significant bits of the CLA byte
        originChannel = types.channel(apdu)
        # FIXME: already checked by calling function
        if originChannel > types.MAX_ORIGIN_CHANNELS - 1:
            sw = types_g.sw.CLASS_NOT_SUPPORTED
            return data, sw

        targetChannel = p2
        if targetChannel > types.MAX_LOGICAL_CHANNELS - 1:
            sw = types_g.sw.INVALID_INSTRUCTION
            return data, sw

        if p1 == types.MANAGE_CHANNEL_OPEN:
            # FIXME: already checked by calling function
            if self.logicalChannel[originChannel].isOpen == False:
                # error: origin channel is not open
                sw = types_g.sw.LOGICAL_CHANNEL_NOT_SUPPORTED
                return data, sw

            if targetChannel == 0:
                # A non-zero channel number assigned by the card from 1 to 3
                # find and assign a first free channel
                targetChannel = self.getFirstFreeChannelNumber()
                if targetChannel == None:
                    sw = types_g.sw.INVALID_INSTRUCTION
                    return data, sw
                data.append(targetChannel)

            if self.logicalChannel[targetChannel].isOpen == True:
                # error: target channel is already open
                sw = types_g.sw.INCORRECT_PARAMETERS_P1_P2
                return data, sw

            # Open the channel
            self.logicalChannel[targetChannel].isOpen = True

            if originChannel == 0:
                #  basic logical channel
                self.logicalChannel[targetChannel].currentDir = "./mf"
                self.logicalChannel[targetChannel].currentFile = None
            else:
                # non-basic logical channel
                self.logicalChannel[targetChannel].currentDir = \
                    self.currentChannel.currentDir
                self.logicalChannel[targetChannel].currentFile = \
                    self.currentChannel.currentFile

        elif p1 == types.MANAGE_CHANNEL_CLOSE:
            if self.logicalChannel[originChannel].isOpen != True:
                # error: origin channel is not open
                sw = types_g.sw.LOGICAL_CHANNEL_NOT_SUPPORTED
                return data, sw
            if self.logicalChannel[targetChannel].isOpen == False:
                # warning: channel to be closed is not open
                sw = types_g.sw.WARNING_CARD_STATE_UNCHANGED
                return data, sw

            if targetChannel == 0:
                # the channel numbered in CLA (a non-zero channel number)
                # shall be closed
                if originChannel == 0:
                    # error: channel 0 (basic) cannot be closed
                    sw = types_g.sw.INVALID_INSTRUCTION
                    return data, sw
                else:
                    targetChannel = originChannel

            # Close the channel
            self.logicalChannel[targetChannel].isOpen = False
        else:
            # error: wrong manage command
            sw = types_g.sw.INVALID_INSTRUCTION
            return data, sw

        sw = self.swNoError()
        return data, sw

    def authenticate(self, apdu):
        data = []
        ins = types.ins(apdu)
        p1 = types.p1(apdu)
        p2 = types.p2(apdu)
        lc = types.p3(apdu)
        dataField = types.dataLc(apdu)

        if self.simType == types.TYPE_SIM:
            if p1 or p2:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw
            if lc != 0x11:
                sw = types_g.sw.WRONG_LENGTH
                return data, sw
        else: # TYPE_USIM
            if p1:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw
            if lc not in (0x11, 0x22):
                sw = types_g.sw.WRONG_LENGTH
                return data, sw
            if self.currentChannel.currentAdf == None:
                # No ADF is active.
                sw = types_g.sw.ERROR_CARD_STATE_UNCHANGED
                return data, sw
            if "ADF" not in self.currentChannel.currentDir:
                sw = 0x6F01 # Current DF not under the ADF.
                return data, sw
            #TODO: check if successful PIN verification (if enabled)
            #      procedure has been performed

        rand = hextools.bytes2hex(types.getValue(dataField, keepData=False))
        autn = hextools.bytes2hex(types.getValue(dataField, keepData=False))
        amf = autn[12:16]
        response = sim_auth.authenticateDummyXor(
                        rand,
                        sim_codes.defaultCard[sim_codes.AUTH_KEY],
                        sim_codes.defaultCard[sim_codes.AUTH_SQN],
                        amf,
                        autn)
        if not response:
            sw = types_g.sw.AUTHENTICATION_ERROR_APPLICATION_SPECIFIC
            return [], sw
        self.responseData = hextools.hex2bytes(response)
        if self.simType == types.TYPE_SIM:
            sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_2G
        else:
            sw1 = types_g.sw1.RESPONSE_DATA_AVAILABLE_3G
        sw2 = len(self.responseData)
        sw = types.packSw(sw1, sw2)

        return data, sw

    def verifyPin(self, apdu):
        data = []

        if types.p1(apdu):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        lc = types.p3(apdu)
        if self.simType == types.TYPE_SIM:
            if lc != 8:
                sw = types_g.sw.WRONG_LENGTH
                return data, sw
            try:
                chv = types_g.verifyChvP2_2g[types.p2(apdu)]
            except:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw
        else:
            if lc not in (0, 8, None):
                sw = types_g.sw.WRONG_LENGTH
                return data, sw
            try:
                chv = types_g.verifyChvP2_3g[types.p2(apdu)]
            except:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw

        if lc:
            # PIN verification procedure.
            pinEnabled = self.simXml.enabledChv(chv)
            if not pinEnabled:
                # PIN is disabled.
                if self.simType == types.TYPE_SIM:
                    sw = types_g.sw.GSM_CHV_ALREADY_VALIDATED
                else:
                    sw = types_g.sw.REFERNCE_DATA_INVALIDATE # 0x6984
                return data, sw

            if self.simXml.remaningAttemptsChv(chv) == 0:
                # PIN is blocked.
                if self.simType == types.TYPE_SIM:
                    sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
                else:
                    sw = types_g.sw.AUTHENTICATION_METHOD_BLOCKED
                return data, sw

            # The PIN / Secret code value.
            value = types.removeTrailingBytes(types.dataLc(apdu), 0xFF)
            value = hextools.bytes2hex(value).decode('hex')
            if self.simXml.getValueChv(chv) == value:
                # Verify OK.
                self.simXml.setVerifiedChv(chv, 1)
                self.simXml.resetAttemptsChv(chv)
                sw = self.swNoError()
                return data, sw
            # Verification failed.
            self.simXml.decrementRemaningAttemptsChv(chv)
        # Empty data field or incorrect PIN
        attemptsLeft = self.simXml.remaningAttemptsChv(chv)
        if self.simType == types.TYPE_SIM:
            if attemptsLeft > 0:
                sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
            else:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
        else:
            sw1 = types_g.sw1.CODE_ATTEMPTS_LEFT
            sw2 = 0xC0 | attemptsLeft
            sw = types.packSw(sw1, sw2)
        return data, sw

    def unblockPin(self, apdu):
        data = []

        if types.p1(apdu):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        lc = types.p3(apdu)
        if self.simType == types.TYPE_SIM:
            if lc != 16:
                sw = types_g.sw.WRONG_LENGTH
                return data, sw
            try:
                chv = types_g.verifyChvUnblockP2[types.p2(apdu)]
            except:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw
        else:
            if lc not in (0, 16, None):
                sw = types_g.sw.WRONG_LENGTH
                return data, sw
            try:
                chv = types_g.verifyChvP2_3g[types.p2(apdu)]
            except:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw

        chvUnblock = "%s_unblock" %chv
        if lc:
            # Unblock and New PIN values.
            value1 = apdu[5:13] # Unblock PIN
            value2 = apdu[13:21] # New PIN
            value2 = types.removeTrailingBytes(value2, 0xFF)
            value1 = hextools.bytes2hex(value1).decode('hex')
            value2 = hextools.bytes2hex(value2).decode('hex')
            if value1 == self.simXml.getValueChv(chvUnblock):
                self.simXml.resetAttemptsChv(chvUnblock)
                chv = chvUnblock.replace("_unblock", "")
                self.simXml.setVerifiedChv(chv, 1)
                self.simXml.resetAttemptsChv(chv)
                self.simXml.setValueChv(chv, value2)
                sw = self.swNoError()
                return data, sw
            # Unblock failed.
            self.simXml.decrementRemaningAttemptsChv(chvUnblock)
        # Empty data field or incorrect PIN
        attemptsLeft = self.simXml.remaningAttemptsChv(chvUnblock)
        if self.simType == types.TYPE_SIM:
            if attemptsLeft > 0:
                sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
            else:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
        else:
            sw1 = types_g.sw1.CODE_ATTEMPTS_LEFT
            sw2 = 0xC0 | attemptsLeft
            sw = types.packSw(sw1, sw2)
        return data, sw

    def disablePin(self, apdu):
        data = []

        if types.p1(apdu):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        lc = types.p3(apdu)
        try:
            if self.simType == types.TYPE_SIM:
                chv = types_g.verifyChvP2_2g[types.p2(apdu)]
            else:
                chv = types_g.verifyChvP2_3g[types.p2(apdu)]
        except:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        if lc != 8:
            sw = types_g.sw.WRONG_LENGTH
            return data, sw

        pinEnabled = self.simXml.enabledChv(chv)
        if not pinEnabled:
            # PIN already disabled.
            if self.simType == types.TYPE_SIM:
                sw = types_g.sw.GSM_CHV_ALREADY_VALIDATED
            else:
                sw = types_g.sw.WARNING_CARD_STATE_UNCHANGED
            return data, sw

        if self.simXml.remaningAttemptsChv(chv) == 0:
            # PIN is blocked.
            if self.simType == types.TYPE_SIM:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
            else:
                sw = types_g.sw.AUTHENTICATION_METHOD_BLOCKED
            return data, sw

        # The PIN / Secret code value.
        value = types.removeTrailingBytes(types.dataLc(apdu), 0xFF)
        value = hextools.bytes2hex(value).decode('hex')
        if self.simXml.getValueChv(chv) == value:
            # Verify OK.
            self.simXml.setEnabledChv(chv, 0)
            self.simXml.setVerifiedChv(chv, 1)
            self.simXml.resetAttemptsChv(chv)
            sw = self.swNoError()
            return data, sw
        # Verification failed.
        self.simXml.decrementRemaningAttemptsChv(chv)
        attemptsLeft = self.simXml.remaningAttemptsChv(chv)
        if self.simType == types.TYPE_SIM:
            if attemptsLeft > 0:
                sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
            else:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
        else:
            sw1 = types_g.sw1.CODE_ATTEMPTS_LEFT
            sw2 = 0xC0 | attemptsLeft
            sw = types.packSw(sw1, sw2)
        return data, sw

    def enablePin(self, apdu):
        data = []

        if types.p1(apdu):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        lc = types.p3(apdu)
        try:
            if self.simType == types.TYPE_SIM:
                chv = types_g.verifyChvP2_2g[types.p2(apdu)]
            else:
                chv = types_g.verifyChvP2_3g[types.p2(apdu)]
        except:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        if lc != 8:
            sw = types_g.sw.WRONG_LENGTH
            return data, sw

        pinEnabled = self.simXml.enabledChv(chv)
        if pinEnabled:
            # PIN was enabled.
            if self.simType == types.TYPE_SIM:
                sw = types_g.sw.GSM_CHV_ALREADY_VALIDATED
            else:
                sw = types_g.sw.WARNING_CARD_STATE_UNCHANGED
            return data, sw

        if self.simXml.remaningAttemptsChv(chv) == 0:
            # PIN is blocked.
            if self.simType == types.TYPE_SIM:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
            else:
                sw = types_g.sw.AUTHENTICATION_METHOD_BLOCKED
            return data, sw

        # The PIN / Secret code value.
        value = types.removeTrailingBytes(types.dataLc(apdu), 0xFF)
        value = hextools.bytes2hex(value).decode('hex')
        if self.simXml.getValueChv(chv) == value:
            # Verify OK.
            self.simXml.setEnabledChv(chv, 1)
            self.simXml.setVerifiedChv(chv, 1)
            self.simXml.resetAttemptsChv(chv)
            sw = self.swNoError()
            return data, sw
        # Verification failed.
        self.simXml.decrementRemaningAttemptsChv(chv)
        attemptsLeft = self.simXml.remaningAttemptsChv(chv)
        if self.simType == types.TYPE_SIM:
            if attemptsLeft > 0:
                sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
            else:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
        else:
            sw1 = types_g.sw1.CODE_ATTEMPTS_LEFT
            sw2 = 0xC0 | attemptsLeft
            sw = types.packSw(sw1, sw2)
        return data, sw

    def changePin(self, apdu):
        data = []

        if types.p1(apdu):
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        lc = types.p3(apdu)
        try:
            if self.simType == types.TYPE_SIM:
                chv = types_g.verifyChvP2_2g[types.p2(apdu)]
            else:
                chv = types_g.verifyChvP2_3g[types.p2(apdu)]
        except:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        if lc != 16:
            sw = types_g.sw.WRONG_LENGTH
            return data, sw

        pinEnabled = self.simXml.enabledChv(chv)
        if not pinEnabled:
            # PIN disabled.
            if self.simType == types.TYPE_SIM:
                sw = types_g.sw.GSM_CHV_ALREADY_VALIDATED
            else:
                sw = types_g.sw.REFERNCE_DATA_INVALIDATE # 0x6984
            return data, sw

        if self.simXml.remaningAttemptsChv(chv) == 0:
            # PIN is blocked.
            if self.simType == types.TYPE_SIM:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
            else:
                sw = types_g.sw.AUTHENTICATION_METHOD_BLOCKED
            return data, sw

        # Old and New PIN values.
        value1 = apdu[5:13] # Old PIN
        value2 = apdu[13:21] # New PIN
        value2 = types.removeTrailingBytes(value2, 0xFF)
        value1 = hextools.bytes2hex(value1).decode('hex')
        value2 = hextools.bytes2hex(value2).decode('hex')
        if value1 == self.simXml.getValueChv(chv):
            self.simXml.setVerifiedChv(chv, 1)
            self.simXml.resetAttemptsChv(chv)
            self.simXml.setValueChv(chv, value2)
            sw = self.swNoError()
            return data, sw

        # Unblock failed.
        self.simXml.decrementRemaningAttemptsChv(chv)
        attemptsLeft = self.simXml.remaningAttemptsChv(chv)
        if self.simType == types.TYPE_SIM:
            if attemptsLeft > 0:
                sw = types_g.sw.GSM_ACCESS_CONDITION_NOT_FULFILLED
            else:
                sw = types_g.sw.GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION
        else:
            sw1 = types_g.sw1.CODE_ATTEMPTS_LEFT
            sw2 = 0xC0 | attemptsLeft
            sw = types.packSw(sw1, sw2)
        return data, sw

    def deactivateFile(self, apdu):
        data = []

        p1 = types.p1(apdu)
        p2 = types.p2(apdu)
        dataField = types.dataLc(apdu)

        if p2:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        if not p1 and not dataField:
            # The command applies on the current EF.
            if self.currentChannel.currentFile == None:
                sw = types_g.sw.COMMAND_NOT_ALLOWED_NO_EF_SELECTED
                return data, sw
            file = self.simXml.findFile(self.currentChannel.currentFile)
        else:
            selectType = p1
            if selectType == types.SELECT_DF_EF_MF:
                file = self.selectByFileId(types.fileId(apdu))
            elif selectType == types.SELECT_BY_PATH_FROM_MF:
                pathToSelect = hextools.bytes2hex(dataField)
                file = self.selectByPathFromMf(pathToSelect)
            elif selectType == types.SELECT_BY_PATH_FROM_DF:
                raise Exception("Selecting by path from DF is not implemented")
            else:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw

        if file == None:
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw
        if self.simXml.getFileType(file) != types.FILE_TYPE_EF:
            sw = types_g.sw.COMMAND_NOT_ALLOWED_NO_EF_SELECTED
            return data, sw

        if self.simXml.isFileEnabled(file):
            # Current file is already deactivated / invalidate.
            sw = types_g.sw.SELECTED_FILE_INVALIDATED
            return data, sw

        sw = self.checkAccessCondition(file, types.AM_EF_DEACTIVATE)
        if sw != self.swNoError():
            return data, sw

        self.simXml.setFileDisabled(file)

        filePath = self.simXml.getPathFromFile(file)
        self.currentChannel.currentFile = filePath
        fileDirPath = self.simXml.getParentDir(filePath)
        self.currentChannel.currentDir = fileDirPath

        sw = self.swNoError()
        return data, sw

    def activateFile(self, apdu):
        data = []

        p1 = types.p1(apdu)
        p2 = types.p2(apdu)
        dataField = types.dataLc(apdu)

        if p2:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        if not p1 and not dataField:
            # The command applies on the current EF.
            if self.currentChannel.currentFile == None:
                sw = types_g.sw.COMMAND_NOT_ALLOWED_NO_EF_SELECTED
                return data, sw
            file = self.simXml.findFile(self.currentChannel.currentFile)
        else:
            selectType = p1
            if selectType == types.SELECT_DF_EF_MF:
                file = self.selectByFileId(types.fileId(apdu))
            elif selectType == types.SELECT_BY_PATH_FROM_MF:
                pathToSelect = hextools.bytes2hex(dataField)
                file = self.selectByPathFromMf(pathToSelect)
            elif selectType == types.SELECT_BY_PATH_FROM_DF:
                raise Exception("Selecting by path from DF is not implemented")
            else:
                sw = types_g.sw.WRONG_PARAMETERS_P1_P2
                return data, sw

        if file == None:
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw
        if self.simXml.getFileType(file) != types.FILE_TYPE_EF:
            sw = types_g.sw.COMMAND_NOT_ALLOWED_NO_EF_SELECTED
            return data, sw

        if not self.simXml.isFileEnabled(file):
            # Current file is already valid.
            sw = types_g.sw.WARNING_CARD_STATE_UNCHANGED
            return data, sw

        sw = self.checkAccessCondition(file, types.AM_EF_ACTIVATE)
        if sw != self.swNoError():
            return data, sw

        self.simXml.setFileEnabled(file)

        filePath = self.simXml.getPathFromFile(file)
        self.currentChannel.currentFile = filePath
        fileDirPath = self.simXml.getParentDir(filePath)
        self.currentChannel.currentDir = fileDirPath

        sw = self.swNoError()
        return data, sw

    def createFile(self, apdu):
        data = []
        value = []

        p1 = types.p1(apdu)
        p2 = types.p2(apdu)

        if p1 or p2:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        dataField = types.dataLc(apdu)

        fdb = types.parseFcpTlv(dataField, types.FDB_TAG)

        # Check parent dir of the new file
        parentDir = self.simXml.findFile(self.currentChannel.currentDir)
        if parentDir == None:
            sw = types_g.sw.SECURITY_STATUS_NOT_SATISFIED #TB checked
            return data, sw

        if fdb[0] & types_g.fileDescriptor.DF_OR_ADF:
            isDfOrAdf = True
            accessMode = types.AM_DF_CREATE_FILE_DF
        else:
            isDfOrAdf = False
            accessMode = types.AM_DF_CREATE_FILE_EF

        sw = self.checkAccessCondition(parentDir, accessMode)
        if sw != self.swNoError():
            return data, sw

        if fdb[0] & types_g.fileDescriptor.SHAREABLE:
            shareable = True
        else:
            shareable = False
        fid = types.parseFcpTlv(dataField, types.FID_TAG)
        fidInt = types.bytes2int(fid)
        fidStr = "%X" % fidInt
        if self.simXml.findFileInDir(self.currentChannel.currentDir, fidStr):
            sw = types_g.sw.FILE_ID_ALREADY_EXISTS
            return data, sw
        aid = types.parseFcpTlv(dataField, types.DF_NAME_TAG)
        if aid != None and self.simXml.findAdf(aid):
            sw = types_g.sw.DF_NAME_ALREADY_EXISTS
            return data, sw
        lcsi =  types.parseFcpTlv(dataField, types.LCSI_TAG)
        secAtrr = types.parseFcpTlv(dataField, types.SECURITY_ATTRIB_REF_EXPANDED)
        if secAtrr != None:
            arrId = secAtrr[0:2]
            arrRule = secAtrr[2]
        else:
            secAtrr = types.parseFcpTlv(dataField, types.SECURITY_ATTRIB_EXPANDED_TAG)
            if secAtrr != None:
                if types.bytes2int(fid) in [types.EF_ARR_MF, types.EF_ARR]:
                    value = secAtrr
                    # set ARR to itself
                    arrId = fid
                    arrRule = 1
                else:
                    raise Exception("Security Expanded attribute is not supported for not EF_ARR files")
            else:
                secAtrr = types.parseFcpTlv(dataField, types.SECURITY_ATTRIB_COMPACT_TAG)
                if secAtrr != None:
                    arrId = secAtrr[0:2]
                    arrRule = secAtrr[2]
                    #raise Exception("Security Compact attribute is not supported")

        path = self.currentChannel.currentDir

        if isDfOrAdf:
            # directory file
            totalFileSize = types.parseFcpTlv(dataField, types.TOTAL_FILE_SIZE_TAG) # unused
            doTempl = types.parseFcpTlv(dataField, types.PIN_STATUS_TEMPLETE_DO_TAG) # unused
            file = self.simXml.createDirectory(path,
                                        fidInt,
                                        types.bytes2int(arrId),
                                        arrRule,
                                        aid)
            self.currentChannel.currentDir = self.simXml.getPathFromFile(file)
            self.currentChannel.currentFile = None
            #TODO:update current Adf!?
        else:
            # elementary file
            fileStruct = types.getFileStructureFromFileDescriptor(fdb[0]) #FIXME: valid for 3G only!
            fileSize = types.parseFcpTlv(dataField, types.FILE_SIZE_TAG)
            sfi = types.parseFcpTlv(dataField, types.SFI_TAG)
            prop = types.parseFcpTlv(dataField, types.PROPRIETARY_TAG)
            if prop != None:
                fillPattern = types.parseTlv(prop, types.FILLING_PATTERN)
                if fillPattern != None:
                    value = fillPattern
                    #TODO: All remaining bytes (if any) shall be initialized with the value
                    # of the last byte of the Filling Pattern - currently filled with 0xFF.
            if fileStruct != types.FILE_STRUCTURE_TRANSPARENT:
                recordLength = types.bytes2int(fdb[2:4])
                if len(value) > recordLength:
                    value = value[:recordLength] # trancate data
            else:
                recordLength = 0

            file = self.simXml.createFile(path,
                                   fidInt,
                                   fileStruct,
                                   types.bytes2int(fileSize),
                                   recordLength,
                                   types.bytes2int(arrId),
                                   arrRule,
                                   value)
            self.currentChannel.currentFile = self.simXml.getPathFromFile(file)
            if fileStruct == types.FILE_STRUCTURE_CYCLIC:
                self.currentChannel.currentRecord = self.simXml.getFileNumberOfRecords(file)
            else:
                self.currentChannel.currentRecord = None

        sw = self.swNoError()
        return data, sw

    def deleteFile(self, apdu):
        data = []

        p1 = types.p1(apdu)
        p2 = types.p2(apdu)

        if p1 or p2:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw

        fid = types.fileId(apdu)
        file = self.selectByFileId(fid)
        if file == None:
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        sw = self.checkAccessCondition(file, types.AM_EF_DELETE)
        if sw != self.swNoError():
            return data, sw

        self.simXml.deleteFile(file)
        if fid == 0x7FFF:
            self.currentChannel.currentDir = "./mf"
        self.currentChannel.currentFile = None

        sw = self.swNoError()
        return data, sw

    def resizeFile(self, apdu):
        # check CLA - 8X
        data = []
        value = None

        p1 = types.p1(apdu)
        p2 = types.p2(apdu)

        if p1 or p2:
            sw = types_g.sw.WRONG_PARAMETERS_P1_P2
            return data, sw
        dataField = types.dataLc(apdu)
        fid = types.bytes2int(types.parseFcpTlv(dataField, types.FID_TAG))
        file = self.selectByFileId(fid)
        if file == None:
            sw = types_g.sw.FILE_NOT_FOUND
            return data, sw

        sw = self.checkAccessCondition(file, types.AM_EF_RESIZE)
        if sw != self.swNoError():
            return data, sw

        fileType = self.simXml.getFileType(file)
        if fileType == types.FILE_TYPE_EF:
            fileSize = types.bytes2int(types.parseFcpTlv(dataField, types.FILE_SIZE_TAG))
            fileStruct = self.simXml.getFileStruct(file)
            if fileStruct == types.FILE_STRUCTURE_CYCLIC:
                sw = types_g.sw.COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE
                return data, sw
            elif fileStruct == types.FILE_STRUCTURE_LINEAR_FIXED:
                recordLength = self.simXml.getFileRecordLength(file)
                if fileSize % recordLength or \
                   fileSize == 0:
                    sw = types_g.sw.WRONG_LENGTH
                    return data, sw
        else:
            totalFileSize = types.bytes2int(types.parseFcpTlv(dataField, types.TOTAL_FILE_SIZE_TAG))
            logging.warning("Resize of DF/ADF is not supported")
            #raise Exception("Resize of DF/ADF is not supported")
            sw = self.swNoError()
            return data, sw

        prop = types.parseFcpTlv(dataField, types.PROPRIETARY_TAG)
        if prop != None:
            fillPattern = types.parseTlv(prop, types.FILLING_PATTERN)
            if fillPattern != None:
                value = fillPattern
                if fileStruct != types.FILE_STRUCTURE_TRANSPARENT and \
                    len(value) > recordLength:
                    value = value[:recordLength] # trancate data
            repeatPattern = types.parseTlv(prop, types.REPEAT_PATTERN)
            if repeatPattern != None:
                raise Exception("Repeat Pattern field ('C2') is not implemented")
            maxFileSize = types.parseTlv(prop, types.MAXIMUM_FILE_SIZE)
            if maxFileSize != None:
                raise Exception("Maximum File Size field ('86') is not implemented")

        self.simXml.resizeFile(file, fileSize, value) # For EFs only!

        filePath = self.simXml.getPathFromFile(file)
        if fileType == types.FILE_TYPE_EF:
            self.currentChannel.currentFile = filePath
            if fileStruct == types.FILE_STRUCTURE_LINEAR_FIXED and \
                self.currentChannel.currentRecord > (fileSize / recordLength):
                self.currentChannel.currentRecord = None
        else:
            self.currentChannel.currentDir = filePath #TODO:update current Adf!?
            self.currentChannel.currentFile = None

        sw = self.swNoError()
        return data, sw

    def getAccessConditionsForFile(self, file, accessMode):
        if self.simType == types.TYPE_SIM:
            #TODO: implement handling of security attr for both 2G and 3G
            return [types.AC_ALWAYS], None
        arrId, arrRule = self.simXml.findEfArr(file)
        fileDir = self.currentChannel.currentDir
        fileId = self.simXml.getFileId(file)
        if fileId != "3F00" and self.simXml.getPathFromFile(file) == fileDir:
            # file is the current dir so check arr in parent
            fileDir = types.parentDirFromPath(self.currentChannel.currentDir)
        if arrRule == 0:
            #TODO: For some files like ADN/FDN the Record number SE #01
            # can be set as 0. Check how we should handle it.
            logging.warning("Arr record number is 0. Use first record (1) instead.")
            arrRule = 1
        arrValue = self.simXml.getEfArrRuleValue(self.simXml.getEfArr(fileDir, arrId), arrRule)
        return types.getAccessConditions(arrValue, accessMode)

    def getAccessCondition(self, file, accessMode):
        ''' Returns only the first condition '''
        conditions = self.getAccessConditionsForFile(file, accessMode)[0]
        return conditions[0]

    def unknownInstruction(self):
        sw1 = types_g.sw1.UNKNOWN_INSTRUCTION_CODE
        sw2 = 0x00
        return [], types.packSw(sw1, sw2)