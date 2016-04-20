import types_g
import hextools
import logging
import os
import re
import shlex
import subprocess

TYPE_SIM = 0
TYPE_USIM = 1

#TODO: try to use types.fidFromPath(self.simFiles.findFileFromName('EF_ARR'))
EF_ARR_MF = 0x2F06
EF_ARR = 0x6F06

INVALID_RECORD_NUMBER = 0

DEFAULT_APP_AID = [0xA0,0x00,0x00,0x00,0x87,0x10,0x09,0xFF,0x81,0xFF,0xFF,0x89,0x06,0x02,0x00,0xFF]
DEFAULT_APP_LABEL = "simLAB"

# Selection mode 1
SELECT_DF_EF_MF        = 0b00000000
SELECT_CHILD_DF        = 0b00000001
SELECT_PARRENT_DF      = 0b00000011
SELECT_BY_DF_NAME      = 0b00000100
SELECT_BY_PATH_FROM_MF = 0b00001000
SELECT_BY_PATH_FROM_DF = 0b00001001

# Selection mode 2
SELECT_NO_DATA_RETURNED     = 0b00001100
SELECT_RETURN_FCP_TEMPLATE  = 0b00000100
SELECT_APP_ACTIVATION       = 0b00000000
SELECT_APP_TERMINATION      = 0b01000000
SELECT_APP_FIRST_OR_ONLY_OCCURENCE = 0b00000000
SELECT_APP_LAST_OCCURENCE   = 0b00000001

# Status - coding of P2
STATUS_SELECT_RESPONSE_RETURNED = 0b00000000
STATUS_DF_NAME_RETURNED = 0b00000001
STATUS_NO_DATA_RETURNED = 0b00001100

FILE_STRUCTURE_TRANSPARENT = 0
FILE_STRUCTURE_LINEAR_FIXED = 1
FILE_STRUCTURE_CYCLIC = 3
FILE_STRUCTURE_UNKNOWN = 4

FILE_TYPE_RFU = 0
FILE_TYPE_MF = 1
FILE_TYPE_DF = 2
FILE_TYPE_EF = 4

# Registered application provider IDentifier (RID)
RID_ETSI = 'A000000009'
RID_3GPP = 'A000000087'
RID_3GPP2 = 'A000000343'

# Access mode data objects
AM_DO_BYTE = 0x80
AM_DO_PROP = 0x9C
'''
1 0 0 0 1 - - -  (CLA), i.e., the value of CLA
1 0 0 0 - 1 - -  (INS), i.e., the value of INS
1 0 0 0 - - 1 -  (P1),  i.e., the value of P1
1 0 0 0 - - - 1  (P2),  i.e., the value of P2
'''
AM_DO_CLA  = 0b10001000
AM_DO_INS  = 0b10000100
AM_DO_P1   = 0b10000010
AM_DO_P2   = 0b10000001

# Dfs access mode byte
AM_DF_DELETE_FILE     = 0b01000000
AM_DF_TERMINATE       = 0b00100000
AM_DF_ACTIVATE_FILE   = 0b00010000
AM_DF_DEACTIVATE_FILE = 0b00001000
AM_DF_CREATE_FILE_DF  = 0b00000100
AM_DF_CREATE_FILE_EF  = 0b00000010
AM_DF_DELETE_CHILD    = 0b00000001

# Ef access mode - Access mode byte
AM_EF_DELETE          = 0b01000000
AM_EF_TERMINATE       = 0b00100000
AM_EF_ACTIVATE        = 0b00010000
AM_EF_DEACTIVATE      = 0b00001000
AM_EF_WRITE           = 0b00000100
AM_EF_UPDATE          = 0b00000010
AM_EF_READ            = 0b00000001
# Ef access mode - Command header description
# Command description by the value of INS
AM_EF_INCREASE        = types_g.iso7816.INCREASE
AM_EF_RESIZE          = types_g.iso7816.RESIZE_FILE

# Security condition data object
'''
'90'           0    -                               | Always
'97'           0    -                               | Never
'9E'           1    Security condition byte         | See Table 20
'A4'           Var. Control reference template      | External or user authentication depending on the usage qualifier
'B4','B6','B8' Var. Control reference template      | SM in command and / or response depending on the usage qualifier
'A0'           Var. Security condition data objects | At least one security condition shall be fulfilled (OR template)
'A7'           Var. Security condition data objects | Inversion of the security conditions (NOT template)
'AF'           Var. Security condition data objects | Every security condition shall be fulfilled (AND template)
'''
SC_DO_ALWAYS           = 0x90
SC_DO_NEVER            = 0x97
SC_DO_BYTE             = 0x9E
SC_DO_USER_AUTH_QC     = 0xA4
SC_DO_OR_TEMPLATE_TAG  = 0xA0
SC_DO_NOT_TEMPLATE_TAG = 0xA7
SC_DO_AND_TEMPLATE_TAG = 0xAF

#efArr offsets
AM_LENGTH_OFFSET        = 1
AM_BYTE_OFFSET          = 2
SC_DO_OFFSET            = 3
SC_DO_LENGTH_OFFSET     = 4
KEY_REF_TAG_OFFSET      = 5
KEY_DO_LENGTH_OFFSET    = 6
KEY_DO_VALUE_OFFSET     = 7

# Coding of life cycle status integer
LIFE_CYCLE_STATE_NO_INFO_GIVEN  = 0x00
LIFE_CYCLE_STATE_CREATION       = 0x01
LIFE_CYCLE_STATE_INIT           = 0x03
LIFE_CYCLE_STATE_OPER_ACTIVATED = 0x05
LIFE_CYCLE_STATE_OPER_DEACTIVATED = 0x04
LIFE_CYCLE_STATE_TERMINATION    = 0x0C

#key reference tag
KEY_REF_TAG = 0x83

#key reference value
'''
01-08 PIN1
81-88 PIN2
0A-0E ADM1-ADM5
'''
KEY_REF_PIN1  = 0x01
KEY_REF_PIN2  = 0x81
KEY_REF_ADM1  = 0x0A
KEY_REF_ADM2  = 0x0B
KEY_REF_ADM3  = 0x0C
KEY_REF_ADM4  = 0x0D
KEY_REF_ADM5  = 0x0E
KEY_REF_PIN_UNIV  = 0x11

#usage qualifier tag
UQ_TAG = 0x95

#key Reference data user knowledge based
'''
- - - - 1 - - - - use the PIN for verification (Key Reference data user knowledge based)
'''
PIN_VERIFY = 0x8

#access condition
AC_ALWAYS = 0x00
AC_CHV1   = 0x01
AC_CHV2   = 0x02
AC_RFU    = 0x03
AC_ADM1   = 0x04
AC_ADM2   = 0x05
AC_ADM3   = 0x06
AC_ADM4   = 0x07
AC_ADM5   = 0x08
AC_NEVER  = 0x0F
AC_UNKNOWN= 0xFF

# Application tags
APP_TEMPLATE_TAG = 0x61
APP_IDENTIFIER_TAG = 0x4F # AID
APP_LABEL_TAG = 0x50
APP_PATH_TAG = 0x81
# and some more

# manage channel
MANAGE_CHANNEL_OPEN = 0x00
MANAGE_CHANNEL_CLOSE = 0x80 # (1<<8)
MAX_LOGICAL_CHANNELS = 4
MAX_ORIGIN_CHANNELS = 4

#TODO: refactor, same as types_g.selectTag
FILE_LENGTH_EXCLUDING_SI_TAG = 0x80
FILE_LENGTH_INCLUDING_SI_TAG = 0x81
PS_DO_TAG                    = 0x90

#CSG
CSG_TEMPLATE_TAG    = 0xA0
CSG_PLMN_TAG        = 0x80
CSG_INFORMATION_TAG = 0x81

FILE_FORMAT_UNKNOWN        = 0
FILE_FORMAT_ID             = 1
FILE_FORMAT_NAME           = 2
FILE_FORMAT_PATH_ABSOLUTE  = 3
FILE_FORMAT_DF_CURRENT     = 4
FILE_FORMAT_DF_PARENT      = 5
FILE_FORMAT_ADF_ID         = 6
FILE_FORMAT_ADF_NAME       = 7

ARR_ALL_ALWAYS = [0x80, 0x01, 0x5F, 0x90, 0x00, 0x84, 0x01, 0x32,
                  0x90, 0x00, 0x84, 0x01, 0xD4, 0x90, 0x00]
# Limitted access - ALWAYS for Read/DeleteChild and Update/CreateEf commands
ARR_CUSTOM =     [0x80, 0x01, 0x03, 0x90, 0x00, 0xFF, 0xFF, 0xFF, 0xFF,
                  0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

keyRefDict = {AC_ALWAYS : SC_DO_ALWAYS,
              AC_CHV1 : KEY_REF_PIN1,
              AC_CHV2 : KEY_REF_PIN2,
              AC_ADM1 : KEY_REF_ADM1,
              AC_ADM2 : KEY_REF_ADM2,
              AC_ADM3 : KEY_REF_ADM3,
              AC_ADM4 : KEY_REF_ADM4,
              AC_ADM5 : KEY_REF_ADM5,
              AC_NEVER : SC_DO_NEVER}

#FCI
FCP_TEMPLATE_TAG = 0x62
FDM_TEMPLATE_TAG = 0x64
FCI_TEMPLATE_TAG = 0x6F

#For a MF / DF / ADF / EF creation:
#FIXME: same as types_g.selectTag plus some additional tags
DATA_CODING_BYTE                = 0x21
FILE_SIZE_TAG                   = 0x80
TOTAL_FILE_SIZE_TAG             = 0x81
FDB_TAG                         = 0x82 # (M) File Descriptor
FID_TAG                         = 0x83
DF_NAME_TAG                     = 0x84
PROPRITEARY_NO_BERTLV_TAG       = 0x85
PROPRITEARY_SECURITY_ATTRIB_TAG = 0x86
EF_FCI_EXTENSION                = 0x87
SFI_TAG                         = 0x88
LCSI_TAG                        = 0x8A # (M)
SECURITY_ATTRIB_COMPACT_TAG     = 0x8B # (M)*
SECURITY_ATTRIB_REF_EXPANDED    = 0x8C # (M)*
PROPRIETARY_TAG                 = 0xA5 # (O)
SECURITY_ATTRIB_EXPANDED_TAG    = 0xAB # (M)*
PIN_STATUS_TEMPLETE_DO_TAG      = 0xC6


DF_AID_TAG                      = 0x84 # (O)
# *Exactly one of the tags should be present

# Proprietary information ('A5') - all optional
SPECIAL_FILE_INFORMATION        = 0xC0
FILLING_PATTERN                 = 0xC1
REPEAT_PATTERN                  = 0xC2
MAXIMUM_FILE_SIZE               = 0x86
FILE_DETAILS                    = 0x84
GSM_ACCESS_CONDITION_TAG        = 0x90
FILE_SHARING_INFO_TAG           = 0x91
EFARR_ACCESS_RULE_SE01_TAG      = 0xAA
EFARR_ACCESS_RULE_SE00_TAG      = 0xAB

#network name
FULL_NW_NAME_TAG                = 0x43
SHORT_NW_NAME_TAG               = 0x45
ADDITIONAL_INFORMATION_PLMN_TAG = 0x80

def cla(apdu):
    return apdu[0]

def ins(apdu):
    return apdu[1]

def p1(apdu):
    return apdu[2]

def p2(apdu):
    return apdu[3]

def p3(apdu):
    try:
        return apdu[4]
    except:
        return None

def dataLc(apdu):
    try:
        return apdu[5 : (5 + p3(apdu))]
    except:
        return None

def le(apdu):
    leIdx = 5 + p3(apdu)
    if len(apdu) > leIdx:
        return apdu[leIdx]
    else:
        return None

def binaryOffset(apdu):
    if p1(apdu) & types_g.binaryCmdP1.SFI_MODE:
        offset = p2(apdu)
    else:
        offset = (p1(apdu) << 8) + p2(apdu)
    return offset

def channel(apdu):
    return apdu[0] & 0b00000011

def returnType(apdu):
    return p2(apdu) & 0b00001100

def appControl(apdu):
    return p2(apdu) & 0b11110000

def fileId(apdu):
    return apdu[-2] * 256 + apdu[-1]

def aid(apdu):
    return dataLc(apdu)

def insName(apdu):
    _ins = ins(apdu)
    try:
        return types_g.iso7816[_ins]
    except:
        return "%02X" %_ins

def sw1(rapdu):
    return rapdu[-2]

def sw2(rapdu):
    return rapdu[-1]

def sw(rapdu):
    return (sw1(rapdu)<<8) + sw2(rapdu)

def swName(sw1, sw2):
    if sw1 == None and sw2 == None:
        return None,  None
    sw = packSw(sw1, sw2)
    try:
        swName = types_g.sw[sw]
    except:
        swName = "%04X" %sw

    try:
        sw1Name = types_g.sw1[sw1]
    except:
        sw1Name = "%02X" %sw1
    return sw1Name, swName

def assertSw(sw1, sw2, checkSw=None, checkSw1=None, log=True, raiseException=False):
    sw1Name, swReceived = swName(sw1, sw2)
    if (checkSw and
        checkSw != swReceived and
        not (checkSw == types_g.sw[types_g.sw.NO_ERROR] and sw1 == types_g.sw1.NO_ERROR_PROACTIVE_DATA)):
        if checkSw != swReceived:
            errorString = "Incorrect SW: %s, expecting: %s. SW1=%s" %(swReceived, checkSw, sw1Name)
            if raiseException:
                raise Exception(errorString)
            else:
                if log:
                    logging.error(errorString)
                else:
                    logging.debug(errorString)
                return True
    elif checkSw1:
        if checkSw1 != sw1Name:
            errorString = "Incorrect SW1: %s, expecting: %s. SW=%s" %(sw1Name, checkSw1, swReceived)
            if raiseException:
                raise Exception(errorString)
            else:
                if log:
                    logging.error(errorString)
                else:
                    logging.debug(errorString)
                return True
    return False

def swNoError(rapdu):
    if sw1(rapdu) == 0x91 or (sw1(rapdu) == 0x90 and sw2(rapdu) == 0x00):
        return True
    else:
        return False

def responseData(rapdu):
    return rapdu[0:-2]

def packSw(sw1, sw2):
    return (sw1<<8) + sw2

def unpackSw(sw):
    sw1 = sw >> 8
    sw2 = sw & 0x0F
    return sw1, sw2

def removeTrailingBytes(array, pattern):
    i = 0
    for byte in array:
        if byte == pattern:
            break
        i += 1
    return array[0:i]

def addTrailingBytes(hexStr, pattern, size):
    if len(hexStr) % 2:
        hexStr += 'F'
    length = size - len(hexStr)/2
    if length > 0:
        hexStr += ("%02X" %pattern) * length
    return hexStr

def getEfAccessMode(byte):
    accesMode = []
    '''
    0 1 - - - - - - DELETE FILE
    0 - 1 - - - - - TERMINATE EF
    0 - - 1 - - - - ACTIVATE FILE
    0 - - - 1 - - - DEACTIVATE FILE
    - - - - - 1 - - WRITE BINARY, WRITE RECORD, APPEND RECORD
    - - - - - - 1 - UPDATE BINARY, UPDATE RECORD, ERASE BINARY, ERASE RECORD(S)
    - - - - - - - 1 READ BINARY, READ RECORD (S), SEARCH BINARY, SEARCH RECORD
    '''
    if byte & AM_EF_DELETE:
        accesMode.append(AM_EF_DELETE)
    if byte & AM_EF_TERMINATE:
        accesMode.append(AM_EF_TERMINATE)
    if byte & AM_EF_ACTIVATE:
        accesMode.append(AM_EF_ACTIVATE)
    if byte & AM_EF_DEACTIVATE:
        accesMode.append(AM_EF_DEACTIVATE)
    if byte & AM_EF_WRITE:
        accesMode.append(AM_EF_WRITE)
    if byte & AM_EF_UPDATE:
        accesMode.append(AM_EF_UPDATE)
    if byte & AM_EF_READ:
        accesMode.append(AM_EF_READ)
    return accesMode

def getValue(data, keepData=True):
    if keepData:
        dataTmp = list(data)
    else:
        dataTmp = data
    length = dataTmp.pop(0)
    if not length:
        return None
    responseData = dataTmp[:length]
    del dataTmp[:length]
    return responseData

def parseTlvMain(data, mainTlv, tag):
    dataTmp = list(data)
    tlvTag = dataTmp.pop(0)
    if tlvTag != mainTlv:
        return None
    length = dataTmp.pop(0) # length
    return parseTlv(dataTmp, tag)

def parseTlv(data, tag, keepData=True):
    if keepData:
        dataTmp = list(data)
    else:
        dataTmp = data

    while len(dataTmp):
        tlvTag = dataTmp.pop(0) # local info tag
        length = dataTmp.pop(0) # length
        if length:
            responseData = dataTmp[:length]
            del dataTmp[:length]
        else:
            responseData = []
        if tag == tlvTag:
            return responseData
    return None

def addTlv(data, tag, parameters):
    data.append(tag)
    data.append(len(parameters))
    data.extend(parameters)
    return data

def addMainTlv(data, tag):
    dataLength = len(data)/2
    data = "%02X%02X%s" %(tag, dataLength, data)
    return data

def parseFcpTlv(data, tag):
    return parseTlvMain(data, FCP_TEMPLATE_TAG, tag)

def parseCsgTlv(data, tag):
    return parseTlvMain(data, CSG_TEMPLATE_TAG, tag)

def getAidFromDirRecord(data):
    return parseTlvMain(data, APP_TEMPLATE_TAG, APP_IDENTIFIER_TAG)

def getKeyRefFromAm(value):
    ''' The KEY_REF_TAG ('83') tag, defining which Secret Code is to be verified '''
    lenKeyRef = value.pop(0)
    if lenKeyRef:
        keyRef = value.pop(0)
        uqTag = value.pop(0)
        if uqTag != UQ_TAG:
            logging.error("User qualifier tag %02X not expected" %uqTag)

        uqLen = value.pop(0)
        if uqLen:
            pinVerify = value.pop(0)
            if pinVerify != PIN_VERIFY:
                logging.error("PIN verify tag %02X not expected" %pinVerify)
    return keyRef

def getKeyFromUserAuthScdo(value):
    ''' Parse SC_DO_USER_AUTH_QC ('A4') tag '''
    keyRefTag = value.pop(0)
    if keyRefTag not in [KEY_REF_TAG]:
        logging.error("Key reference tag %02X not expected" %keyRefTag)
    return getKeyRefFromAm(value)

def parseEfArrRuleAmDo(value):
    accessModes = []
    keys = []
    template = None

    amDoType = value[0]
    if amDoType == AM_DO_BYTE:
        amDoByte = parseTlv(value, AM_DO_BYTE, keepData=False)
        accessModes = getEfAccessMode(amDoByte[0])
    elif amDoType == AM_DO_INS:
        amDoIns = parseTlv(value, AM_DO_INS, keepData=False)
        accessModes.append(amDoIns[0]) # 'D4' - RESIZE or '32' - INCREASE
    else:
        #TODO: implement
        logging.error("Access mode tag %02X not implemented" %amDoType)
        nextAmDo = len(value)
        return nextAmDo, accessModes, keys

    scDo = value.pop(0)
    length = value.pop(0)
    nextAmDo = value[length:]

    if scDo in [SC_DO_ALWAYS, SC_DO_NEVER]:
        keys.append(scDo)
    elif scDo == SC_DO_USER_AUTH_QC:
        keys.append(getKeyFromUserAuthScdo(value))
    elif scDo in [SC_DO_OR_TEMPLATE_TAG,
                SC_DO_NOT_TEMPLATE_TAG,
                SC_DO_AND_TEMPLATE_TAG]:
        template = scDo
        while(value):
            scDo = value.pop(0)
            length = value.pop(0)
            if scDo == SC_DO_USER_AUTH_QC:
                keys.append(getKeyFromUserAuthScdo(value))
            else:
                break
    else:
        logging.error("Security condition tag %02X not supported" %scDo)

    return nextAmDo, accessModes, keys, template

def parseEfArrRule(value):
    access = {}
    amDo = list(value)

    while amDo[0] != 0xFF:
        amDo, accessModes, keys, condMode = parseEfArrRuleAmDo(amDo)
        for accessMode in accessModes:
            access[accessMode] = [keys, condMode]
        if not amDo:
            break;
    return access

def getFileStructureFromFileDescriptor(fileDecriptor):
    structureBits = fileDecriptor & types_g.fileDecriptorMask.EF_STRUCTURE
    if structureBits ==  types_g.fileDescriptor.TRANSPARENT_STRUCTURE:
        structure = FILE_STRUCTURE_TRANSPARENT
    elif structureBits ==  types_g.fileDescriptor.LINEAR_FIXED_STRUCTURE:
        structure = FILE_STRUCTURE_LINEAR_FIXED
    elif structureBits ==  types_g.fileDescriptor.CYCLIC_STRUCTURE:
        structure = FILE_STRUCTURE_CYCLIC
    else:
        structure = FILE_STRUCTURE_UNKNOWN
    return structure


def getAccessConditions(arrValue, accessMode):
    conditions = []
    accesses = parseEfArrRule(arrValue)
    try:
        access = accesses[accessMode]
        keys = access[0]
        condMode = access[1] # template (and, or, not)
    except:
        keys = [SC_DO_NEVER]
        condMode = None

    for key in keys:
        if key == SC_DO_ALWAYS:
            condition = AC_ALWAYS
        elif key == KEY_REF_PIN1:
            condition = AC_CHV1
        elif key == KEY_REF_PIN2:
            condition = AC_CHV2
        elif key == KEY_REF_ADM1:
            condition = AC_ADM1
        elif key == KEY_REF_ADM2:
            condition = AC_ADM2
        elif key == KEY_REF_ADM3:
            condition = AC_ADM3
        elif key == KEY_REF_ADM4:
            condition = AC_ADM4
        elif key == KEY_REF_ADM5:
            condition = AC_ADM5
        elif key == SC_DO_NEVER:
            condition = AC_NEVER
        else:
            raise Exception("Unknown key %02X" %key)
        conditions.append(condition)

    return conditions, condMode

def validPathFormat(path):
    for _file in path.split("/")[0:]:
        if not _file:
            #root dir '/'
            continue
        if _file in ["/", "..", "."]:
            continue
        elif _file.startswith("EF_") or _file.startswith("DF_"):
            continue
        elif _file.startswith("ADF_"):
            continue
        try:
            int(_file, 16)
            if len(_file) != 4:
                logging.warning("File: %s has incorrect length, expected 4" %_file)
                return False
            continue
        except:
            return False
    return True

def getAdfId(adfName):
    adfIdRe = re.compile("ADF(\d)", re.IGNORECASE)
    adfId = adfIdRe.search(adfName)
    if not adfId:
        logging.warning("ADF name not expected: %s" %adfName)
        return None
    return int(adfId.group(1))

def getFileNameFormat(path):
    if not path:
        raise Exception("path is empty")
    path = path.upper()
    if not validPathFormat(path):
        return FILE_FORMAT_UNKNOWN
    if path.startswith("EF_") or path.startswith("DF_"):
        format = FILE_FORMAT_NAME
    elif path.startswith("ADF") and path[3].isdigit():
        format = FILE_FORMAT_ADF_ID
    elif path.startswith("ADF_"):
        format = FILE_FORMAT_ADF_NAME
    elif path.startswith("/"):
        format = FILE_FORMAT_PATH_ABSOLUTE
    elif path.startswith("./") or path == ".":
        format = FILE_FORMAT_DF_CURRENT
    elif path.startswith("../") or path == "..":
        format = FILE_FORMAT_DF_PARENT
    else:
        format = FILE_FORMAT_ID
    return format

def isFidAdf(fid):
    fid = fid.upper()
    return fid.startswith("ADF")

def getAidFromData(data):
    return parseFcpTlv(data, types_g.selectTag.DF_NAME)

def getSfiFromData(data):
    sfi = parseFcpTlv(data, types_g.selectTag.SHORT_FILE_IDENTIFIER)
    if not sfi:
        return 0
    return sfi[0]

def getFileLength(data):
    tagData = parseFcpTlv(data, FILE_LENGTH_EXCLUDING_SI_TAG)
    if tagData == None:
        logging.error("BINARY_LENGTH_TAG not found in FCI")
        return None
    length = tagData[1]
    return length

def getArrFileFromData(data):
    arr = parseFcpTlv(data, SECURITY_ATTRIB_COMPACT_TAG)
    if not arr:
        return None, None
    arrFile = "%02X%02X" %(arr[0], arr[1])
    arrRecord = arr[2]
    return arrFile, arrRecord

def getSecurityAttribFromData(data):
    secAtrr = parseFcpTlv(data, SECURITY_ATTRIB_EXPANDED_TAG)
    return secAtrr

def fidFromPath(path):
    if path == "/":
        return "3F00"
    elif "/" in path:
        if path[-1] == '/':
            path = path[0:-1]
        files = path.split("/")[0:]
        fid = files[-1]
    else:
        fid = path
    return fid

def previousFidFromPath(path):
    if "/" in path:
        files = path.split("/")[1:]
        if len(files) > 1:
            fid = files[-2]
            return fid
    return None

def parentDirFromPath(path):
    if '/' in path:
        if path[-1] == '/':
            path = path[0:-1]
        parrent = "/".join(path.split("/")[0:-1])
        if not parrent:
            parrent = '/'
        return parrent
    else:
        return "../"

def addToPath(path, fileName):
    if (path and
        fileName and
        fileName != "/" and
        path[-1] != "/"):
        path += "/"
    if (path != "/" or fileName != "/"):
        path += fileName
    return path

def getFilesFromPath(path):
    return path.strip("/").split("/")

def getParamValue(data, paramName, splitCharacter=',', separator='='):
    parameters = data.split(splitCharacter)
    for parameter in parameters:
        if parameter.find(paramName) != -1:
            value = re.search("%s%s(.*)" %(paramName, separator), parameter).group(1)
            if value == 'None':
                return None
            else:
                return value
    return None

#get data value returned by sim_shell
def getDataValue(out):
    return re.search("data (.*)", out).group(1)

def getKeyFromDictValue(dictionary, value):
    _dictionary = dict((v,k) for k, v in dictionary.iteritems())
    return _dictionary[value]

### Misc ###
def bytes2int(bytes):
    size = len(bytes)
    return sum(bytes[i] << ((size-i-1) * 8) for i in range(size))

def cmpBitwise(value1, value2, mask=None):
    if mask == None: mask=value2
    if value1 & mask == value2:
        return True
    return False

def isSublist(list1, list2):
    lengthList1 = len(list1)
    lengthList2 = len(list2)
    if lengthList1 > lengthList2:
        return False
    return any(list1 == list2[i:(lengthList1+i)] for i in xrange(lengthList2 - (lengthList1+1)))

def killProcess(name, signal=15):
    if os.name != 'posix':
        #cmd = 'taskkill /f /im ' + name
        cmd = 'taskkill /im /t' + name
    else:
        cmd = "killall -%d %s" %(signal, name)
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out,err
