#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Kamil Wartanowicz

import os
import logging
import plac
import traceback

import sim_router
import file_parser
import sim_codes
import sim_reader
import sim_backup
from util import hextools
from util import types
from util import types_g

def setupLogger():
    logger = logging.getLogger("__name__")
    #dont't propagate to root logger
    logger.propagate=False
    logger.handlers = []
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)
    consoleFormatter = logging.Formatter(fmt='%(message)s')
    consoleHandler.setFormatter(consoleFormatter)
    # add the handlers to the logger
    logger.addHandler(consoleHandler)
    return logger

class SimShell(object):
    "\n===SIM SHELL==="

    commands = (
        'query_code_status',
        'verify_code',
        'force_security_codes',
        'validate_pin1',
        'apdu',
        'cd',
        'read',
        'readi',
        'write',
        'writei',
        'select_sim_card',
        'get_plmn',
        'set_plmn',
        'log_level',
        'open_channel',
        'close_channel',
        'get_ust',
        'set_ust',
        'delete',
        'create',
        'create_arr',
        'pwd',
        'ls',
        'resize',
        'backup',
        'extend',
        'sat',
        'set_active_channel')

    def __init__(self, simCtrl, interactive=False):
        self.simCtrl = simCtrl
        self.forceCodes = True
        self.logger = setupLogger()
        self.interactive = interactive

    def select_sim_card(self, simId):
        """Select active SIM in shell.

        Usage:
            select_sim_card simId

        Args:
            simId: range (0 -- n--1), n -- number of SIM cards.

        Returns:
            status: OK|NOK

        Example::

            />select_sim_card 0
        """
        self.simCtrl.setSrvCtrlId(int(simId))
        return self.responseOk()

    def apdu(self, data, channel=None, mode=None):
        """Send raw APDU to SIM.

        Usage:
            apdu data [channel] [mode]

        Args:
            |  data: raw APDU (hex).
            |  channel: logical channel
            |  mode: inject mode:
            |      INJECT_READY = 0
            |      INJECT_NO_FORWARD = 1
            |      INJECT_WITH_FORWARD = 1

        Returns:
            status: OK|NOK

        Example::

            />apdu 00A40004023F00
            />apdu "00 A4 00 04 02 3F 00"
        """
        data = data.replace(' ', '')
        if channel != None:
            channel = int(channel) != 0
        if mode != None:
            mode = int(mode)
        else:
            mode = sim_router.INJECT_NO_FORWARD
        sw1, sw2, data = self.simCtrl.sendApdu(data, mode=mode)
        return self.responseOk("%s%02X%02X" %(hextools.bytes2hex(data), sw1, sw2))

    def set_active_channel(self, channel):
        """Set active logical channel.

        Usage:
            set_active_channel channel

        Args:
            channel: one of the already opened logical channels

        Returns:
            status: OK|NOK

        Example::

            />set_active_channel 0
        """
        self.simCtrl.setActiveChannel(int(channel))
        return self.responseOk()

    def query_code_status(self, name):
        """Query security code status.

        Usage:
            query_code_status code

        Args:
            code: pin1|pin2|puk1|puk2|adm1|adm4

        Returns:
            |  status: OK|NOK
            |  data:
            |    attempts_left:
            |      range (0--10),
            |      current number of code attempts left.

        Example::

            />query_code_status pin1
            data attempts_left=3
        """
        name = name.lower()
        if name == "pin1":
            attemptsLeft = self.simCtrl.pin1Status()
        elif name == "pin2":
            attemptsLeft = self.simCtrl.pin2Status()
        elif name == "puk1":
            attemptsLeft = self.simCtrl.pin1UnblockStatus()
        elif name == "puk2":
            attemptsLeft = self.simCtrl.pin2UnblockStatus()
        elif name == "adm1":
            attemptsLeft = self.simCtrl.adm1Status()
        elif name == "adm4":
            attemptsLeft = self.simCtrl.adm4Status()
        else:
            return self.responseNok("%s unknown" %name)

        if attemptsLeft == None:
            return self.responseNok()
        return self.responseOk("attempts_left=%d" %attemptsLeft)

    def force_security_codes(self, state):
        """Force verification with default value of security codes.

        Usage:
            force_security_codes state

        Args:
            |  state:
            |    0 -- prompt user every time to verify security code.
            |    1 -- force verification of security codes if there is maximum number of attemps left.

        Returns:
            status: OK|NOK

        Example::

            />force_security_codes 0
        """
        self.forceCodes = int(state)
        return self.responseOk()

    def verify_code(self, name):
        """Verify security code. If force_security_codes is 1, then default
        security codes will be used for verification if there is maximum
        number of attemps left.

        Usage:
            verify_code code

        Args:
            code: pin1|pin2|puk1|puk2|adm1|adm4

        Returns:
            status: OK|NOK

        Example::

            />verify_code pin1
        """
        name = name.lower()
        if name == "pin1":
            pinId = sim_codes.PIN_1
        elif name == "pin2":
            pinId = sim_codes.PIN_2
        elif name == "puk1":
            pinId = sim_codes.PIN_1_UNBLOCK
        elif name == "puk2":
            pinId = sim_codes.PIN_2_UNBLOCK
        elif name == "adm1":
            pinId = sim_codes.ADM_1
        elif name == "adm4":
            pinId = sim_codes.ADM_4
        else:
            return self.responseNok("Unknown code %s" %name)
        status = self.verifyCode(pinId)
        if not status:
            return self.responseNok()
        return self.responseOk()

    def validate_pin1(self, state):
        """Validate PIN1. If force_security_codes is 1, then default
        security codes will be used for verification if there is maximum
        number of attemps left.

        Usage:
            validate_pin1 state

        Args:
            |  state
            |    0 -- unvalidate (disable) PIN1.
            |    1 -- validate (enable) PIN1.

        Returns:
            status: OK|NOK

        Example::

            />validate_pin1 0
        """
        currentState = self.simCtrl.pin1Enabled()
        state = int(state)
        if state != currentState:
            if state:
                code = sim_codes.PIN_1_ENABLE
            else:
                code = sim_codes.PIN_1_DISABLE
            if not self.verifyCode(code):
                return self.responseNok()
        return self.responseOk()

    def get_plmn(self):
        """Get HPLMN (part of EF_IMSI and EF_AD).

        Usage:
            get_plmn

        Returns:
            |  status: OK|NOK
            |  data: MNC (Mobile Country Code) + MNC (Mobile Network Code).

        Example::

            />get_plmn
            data 00101
        """
        path = self.getAbsolutePath("EF_IMSI")
        data = self.readRaw(path)
        if not data:
            return self.responseNok()
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        imsi = self.simCtrl.file_parser.getFileValue(fileName, data)
        if not imsi:
            return self.responseNok()
        mncLength = 2
        if self.simCtrl.router.simType == types.TYPE_USIM:
            path = self.getAbsolutePath("/ADF_USIM/EF_AD")
        else:
            path = self.getAbsolutePath("/7F20/EF_AD")
        adRaw = self.readRaw(path)
        if adRaw:
            adData = hextools.hex2bytes(adRaw)
            if not adData:
                return self.responseNok("Failed to parse EF_AD")
            if len(adData) < 4:
                #For 2G card mnc length is optional in EF_AD
                mncLength = 2
            else:
                mncLength = adData[3]
        mccLength = 3
        plmnLength = mccLength + mncLength
        plmn = imsi[0:plmnLength]
        return self.responseOk("%s" %plmn)

    def set_plmn(self, value):
        """Change HPLMN (part of EF_IMSI and EF_AD).

        Usage:
            set_plmn value

        Args:
            value: MNC (Mobile Country Code) + MNC (Mobile Network Code)

        Returns:
            status: OK|NOK

        Example::

            />set_plmn 00101
            />set_plmn 310410
        """
        plmnLength = len(value)
        if plmnLength not in [5,6]:
            return "SET_PLMN: FAILED. Incorrect length: %d" %plmnLength
        mncLength = len(value[3:])
        if plmnLength == 5:
            value = "%s0" %value

        path = self.getAbsolutePath("EF_IMSI")
        data = self.readRaw(path)
        if not data:
            return self.responseNok()
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        imsi = self.simCtrl.file_parser.getFileValue(fileName, data)
        if not imsi:
            return self.responseNok()

        imsiNew = "%s%s" %(value, imsi[6:])
        path = self.getAbsolutePath("EF_IMSI")
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        data = self.simCtrl.file_parser.setFileValue(fileName, imsiNew)
        status = self.writeRaw(path, data)
        if not status:
            return self.responseNok()

        if self.simCtrl.router.simType == types.TYPE_USIM:
            path = self.getAbsolutePath("/ADF_USIM/EF_AD")
        else:
            path = self.getAbsolutePath("/7F20/EF_AD")
        adRaw = self.readRaw(path)
        if not adRaw:
            if plmnLength > 5:
                return self.responseNok("EF_AD read failed")
            else:
                return self.responseOk()
        adData = hextools.hex2bytes(self.readRaw(path))
        if not adData:
            return self.responseNok("Read EF_AD failed")
        if len(adData) < 4:
            #For 2G card mnc length is optional in EF_AD
            return self.responseNok("EF_AD is too short to set MNC length")
        if adData[3] != mncLength:
            adData[3] = mncLength
            newAdData = hextools.bytes2hex(adData)
            status = self.writeRaw(path, newAdData)
            if not status:
                return self.responseNok("Update EF_AD failed")
            logging.info("EF_AD updated with MNC length:%d" %mncLength)
        return self.responseOk()

    def pwd(self):
        """Get current file path.

        Usage:
            pwd

        Returns:
            |  status: OK|NOK
            |  data:
            |    path: absolute path, DF and ADF end with '/'.
            |    name: file/Directory name.
            |    simId: range (0 -- n--1), n -- number of SIM cards.

        Example::

            /ADF0/6F46>pwd
            data path=/ADF0/6F46,name=EF_SPN,simId=0
        """
        currentFile = self.simCtrl.getCurrentFile()
        path = currentFile.path
        type = currentFile.type
        name = self.simCtrl.simFiles.getNameFromPath(path)
        if types.cmpBitwise(type, types_g.fileDescriptor.DF_OR_ADF):
            path = types.addToPath(path, "/")
        simId = self.simCtrl.srvId
        return self.responseOk("path=%s,name=%s,simId=%d" %(path, name, simId))

    def cd(self, path):
        """Change current file or directory (select file).

        Usage:
            cd path

        Args:
            |  path
            |    Supports following formats:
            |      absolute path
            |        /7F10/5F3A/4F3
            |      reference path
            |        . current selected file
            |      parent DF
            |        .. parrent DF of the current DF
            |      best effort
            |        EF_IMSI
            |          Prority to find file: ADF_USIM, ADF_ISIM, 7F20, MF.
            |      adf names
            |        /ADF_0/6F48 AID in first EF_DIR record
            |        /ADF_USIM/6F48 USIM Aid in EF_DIR
            |        /ADF_ISIM/6F04 ISIM Aid in EF_DIR
            |      combined
            |        /7F10/../ADF_USIM/EF_IMSI

        Returns:
            |  status: OK|NOK
            |  data: get response value (hex)

        Example::

            />cd /
            />cd EF_IMSI
            />cd /ADF0/6F07
            />cd /ADF_USIM/6F07
            />cd /7F20
            />cd DF_GSM
            />cd ./6F07
            />cd ..
            />cd .
        """
        path = self.getAbsolutePath(path)
        if not path:
            return self.responseNok()
        sw1, sw2, data = self.simCtrl.selectFileByPath(path)
        if not data:
            return self.responseNok()
        return self.responseOk("%s" %hextools.bytes2hex(data))

    def ls(self):
        """List files and directories.

        Usage:
            ls

        Returns:
            |  status: OK|NOK
            |  data: childs (EF, DF, ADF) of current selected file.

        Example::

            />ls
            data 7F10/,7F20/,2FE2,2F05,2F06,2F00,ADF_USIM/,ADF_ISIM/,7F21/
        """
        files = self.simCtrl.listFiles()
        fileStr = ",".join(files)
        return self.responseOk("%s" %fileStr)

    def read(self, path):
        """Read raw file data.

        Usage:
            read path

        Args:
            path: check :py:func:`cd` command description.

        Returns:
            |  status: OK|NOK
            |  data: raw file data (hex).
            |    For cyclic or linear fixed files, records are separated by semicolon.

        Example::

            />read EF_IMSI
            080910101032547698
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()
        data = self.readRaw(path)
        if not data:
            return self.responseNok()
        return self.responseOk("%s" %data)

    def readi(self, path):
        """Read file and interpreted file data.

        Usage:
            readi path

        Args:
            path: check :py:func:`cd` command description.

        Returns:
            |  status: OK|NOK
            |  data: interpreted file data.
            |    For cyclic or linear fixed files, records are separated by semicolon.

        Example::

            />readi EF_IMSI
            001010123456789
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()
        data = self.readRaw(path)
        if not data:
            return self.responseNok()
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        data = self.simCtrl.file_parser.getFileValue(fileName, data)
        return self.responseOk("%s" %data)

    def write(self, path, data):
        """Write file with raw data.

        Usage:
            write path data

        Args:
            |  path: check :py:func:`cd` command description.
            |  data: raw data (hex). Separate records by semicolon for cyclic or linear fixed files.

        Returns:
            status: OK|NOK

        Example::

            />write EF_IMSI 080910101032547698
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()
        status = self.writeRaw(path, data)
        if not status:
            return self.responseNok()
        return self.responseOk()

    def writei(self, path, value):
        """Write file with inerpreted data.

        Usage:
            writei path value

        Args:
            |  path: check :py:func:`cd` command description.
            |  value: interpreted data. Separate records by semicolon for cyclic or linear fixed files.

        Returns:
            status: OK|NOK

        Example::

            />writei EF_IMSI 001010123456789
            />writei /ADF_USIM/EF_SPN "name=simLAB.spn,display=1"
            />writei EF_IMPU sip:user@test.3gpp.com;sip:+11234567890@test.3gpp.com
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        data = self.simCtrl.file_parser.setFileValue(fileName, value)
        status = self.writeRaw(path, data)
        if not status:
            return self.responseNok()
        return self.responseOk()

    def create(self, path, param=None):
        """Create file or directory.

        Usage:
            create path [param]

        Args:
            |  path: check :py:func:`cd` command description. To create DF/ADF add '/' at the end of path.
            |  param: file creation parameters.
            |    EF creation
            |      shareable: range (0,1), default 1.
            |      fileType: range (1,2,6), default 2
            |        1 -- TRANSPARENT_STRUCTURE
            |        2 -- LINEAR_FIXED_STRUCTURE
            |        6 -- CYCLIC_STRUCTURE.
            |      fileSize: default 60(hex).
            |      recordLength: default 20(hex).
            |      LcsiValue: default 5(hex).
            |      se01: default 2(hex).
            |      sfi: default 0(hex).
            |    DF/ADF creation
            |      shareable: range (0,1), default 1.
            |      totalFileSize: default 64(hex).
            |      LcsiValue: default 5(hex).
            |      se01: default 2(hex).
            |      sfi: default 0(hex).
            |      aid: Add AID parameter for ADF creation.
            |    After DF creation, EF_ARR is automatically created as well.

        Returns:
            status: OK|NOK

        Example:

        Create directory DEED::

            />create /ADF_USIM/DEED/

        Create directory BEEF and elementary file DEAF::

            />create /ADF_USIM/BEEF/DEAF
        """
        if self.createRaw(path, param):
            return self.responseOk()
        else:
            return self.responseNok()

    def create_arr(self, path, fileParam=None):
        """Create EF_ARR file.

        Usage:
            create_arr path [param]

        Args:
            |  path: check :py:func:`cd` command description. To create DF/ADF add / at the end of path.
            |  param: EF_ARR creation parameters.
            |    shareable: range (0,1), default 1.
            |    LcsiValue: default 5(hex).
            |    nbrOfRecords: default 9(hex).
            |    recordSize: default 60(hex).

        Returns:
            status: OK|NOK

        Example::

            />create_arr /ADF_USIM/DEED/6F06
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()
        if self.createArr(path, fileParam):
            return self.responseOk()
        else:
            return self.responseNok()

    def delete(self, path):
        """Delete file or directory.

        Usage:
            delete path

        Args:
            path: check :py:func:`cd` command description.

        Returns:
            status: OK|NOK

        Example::

            />delete /ADF0/DEED/
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()

        status = self.deleteRaw(path)
        if not status and types.parentDirFromPath(path) in ["/3F00", "/"]:
            # If the parent dir is MF try with a different access mode
            # This is a workaround for Gemalto Sim cards
            status = self.deleteRaw(path, types.AM_DF_DELETE_CHILD)
        if not status:
            return self.responseNok()
        logging.info("File %s deleted." %path)
        return self.responseOk()

    def resize(self, path, newFileSize, fillPattern=None):
        """Resize file or directory. The command is NOT supported by
        Gemalto SIM cards (GemXplore 3G).

        Usage:
            resize path newFileSize [fillPattern]

        Args:
            |  path: check :py:func:`cd` command description.
            |  newFileSize: new size of the file (hex).
            |  fillPattern: the value of the newly allocated memory (hex).
            |               The memory will be filled with 0xFF by default.

        Returns:
            status   OK|NOK

        Example::

            />resize /ADF0/BEEF 6F
            />resize /ADF0/BEEF 6F A5A5A5A5A5A5
        """
        path = self.getAbsolutePath(path)
        if not path:
            return self.responseNok()
        status = self.resizeRaw(path, newFileSize, fillPattern)
        if not status:
            return self.responseNok()
        return self.responseOk()

    def extend(self, path, sizeToExtend):
        """Extend the size of a transparent or a linear fixed file.
        The command is supported by Gemalto SIM cards (GemXplore 3G).

        Usage:
            extend path sizeToExtend

        Args:
            |  path: check :py:func:`cd` command description.
            |  sizeToExtend: specifies the size or the number of records of the extension.
            |                Transparent EF: size of extension (max = 255).
            |                Linear Fixed EF: number of records (max = 254).

        Returns:
            status   OK|NOK

        Example::

            />extend /ADF0/BEEF 2
        """
        path = self.getAbsolutePath(path)
        if not path or not self.selectFile(path):
            return self.responseNok()
        status = self.extendRaw(path, sizeToExtend)
        if not status:
            return self.responseNok()
        return self.responseOk()

    def get_ust(self, serviceId):
        """Get service value from EF_UST.

        Usage:
            get_ust serviceId

        Args:
            serviceId: service number in EF_UST.

        Returns:
            |  status: OK|NOK
            |  data: Service value

        Example::

            />get_ust 17
            data 1
        """
        path = self.getAbsolutePath("EF_UST")
        data = self.readRaw(path)
        if not data:
            return self.responseNok()
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        ustTable = self.simCtrl.file_parser.getFileValue(fileName, data)
        serviceId = int(serviceId)
        if len(ustTable) <= serviceId:
            return self.responseNok("error=ServiceId:%d not available" %serviceId)
        return self.responseOk("%d" %ustTable[serviceId-1])

    def set_ust(self, serviceId, value):
        """Set specified service value in EF_UST.

        Usage:
            set_ust serviceId value

        Args:
            |  serviceId: service number in EF_UST.
            |  value: service value, range (0,1).

        Returns:
            status: OK|NOK

        Example::

            />set_ust 17 1
            data 1
        """
        path = self.getAbsolutePath("EF_UST")
        data = self.readRaw(path)
        if not data:
            return self.responseNok()
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        ustTable = self.simCtrl.file_parser.getFileValue(fileName, data)
        serviceId = int(serviceId)
        value = int(value)
        ustTable[serviceId-1] = value
        fileName = self.simCtrl.simFiles.getNameFromPath(path)
        ustRaw = self.simCtrl.file_parser.setFileValue(fileName, ustTable)
        status = self.writeRaw(path, ustRaw)
        if not status:
            return self.responseNok()
        return self.responseOk()

    def open_channel(self, originChannel, targetChannel):
        """Open logical channel (target) from an origin channel.

        Usage:
            open_channel originChannel targetChannel

        Args:
            |  originChannel: 0 -- basic channel.
            |  targetChannel:
            |    range (0--n), n -- max number of logical channels.
            |    0 -- assign first available logical channel.

        Returns:
            status: OK|NOK

        Example::

            open_channel 0 2
        """
        originChannel = int(originChannel)
        targetChannel = int(targetChannel)
        targetChannel = self.simCtrl.openChannel(originChannel, targetChannel)
        if targetChannel:
            return self.responseOk(str(targetChannel))
        else:
            return self.responseNok()

    def close_channel(self, originChannel, targetChannel):
        """Close the logical channel (target) from an origin channel.

        Usage:
            close_channel originChannel targetChannel

        Args:
            |  originChannel: 0 -- basic channel.
            |  targetChannel: range (1--n), n -- max number of logical channels.
                        Only for already opened channels.

        Returns:
            status: OK|NOK

        Example::

            />close_channel 0 2
        """
        originChannel = int(originChannel)
        targetChannel = int(targetChannel)
        if self.simCtrl.closeChannel(originChannel, targetChannel):
            return self.responseOk()
        else:
            return self.responseNok()

    def log_level(self, level):
        """Configure logging level.

        Usage:
            log_level level

        Args:
            |  level:
            |    0 -- ERROR
            |    1 -- WARNING
            |    2 -- INFO (Default)
            |    3 -- DEBUG

        Returns:
            status: OK|NOK

        Example::

            />log_level 0
        """
        level = int(level)
        if level == 0:
            level = logging.ERROR
            levelStr = "ERROR"
        elif level == 1:
            level = logging.WARNING
            levelStr = "WARNING"
        elif level == 2:
            level = logging.INFO
            levelStr = "INFO"
        elif level >= 3:
            level = logging.DEBUG
            levelStr = "DEBUG"

        logger = logging.getLogger()
        logger.setLevel(level)
        return self.responseOk("logging.%s" %levelStr)

    def backup(self):
        """Backup SIM file system. Output file is saved as
        ../sim_soft/sim_backup_<imsi>.xml. To use the backup file in
        soft SIM, replace the file ../sim_soft/sim_backup.xml.
        Remove ../sim_soft/sim_backup.xml to restore default soft SIM files.

        Usage:
            backup

        Returns:
            |  status: OK|NOK
            |  data: saved xml file path

        Example::

            />backup
            data C:/proj/simlab/sim_soft/sim_backup_001010123456789.xml
        """
        status, data = self.readi("EF_IMSI")
        if not self.statusOk(status):
            return self.responseNok()
        imsi = types.getDataValue(data)
        atr = self.simCtrl.router.getCtrlCard(self.simCtrl.srvId).getCachedAtr()
        atr = hextools.bytes2hex(atr, " ")
        self.simBackup = sim_backup.SimBackup(self.simCtrl, imsi, atr)
        sw1, sw2, data = self.simCtrl.selectMf()
        sw1, sw2, data = self.simCtrl.getResponse(sw2)
        node = self.simBackup.setMf(data)
        status = self._backup("/", node)
        xmlPath = self.simBackup.saveXml()
        xmlPath = os.path.abspath(xmlPath).replace("\\", "/")
        if status:
            return self.responseOk(xmlPath)
        else:
            return self.responseNok()

    def sat(self, param, value=None):
        """Trigger SAT (Sim Application Toolkit) command.

        Usage:
            sat param value

        Args:
            |  param: refresh|apdu
            |  value: depends on param

        Returns:
            status: OK|NOK

        Example::

            />sat refresh 1
            data 1
        """
        softCardDict = self.simCtrl.router.getSoftCardDict()
        if not softCardDict:
            return self.responseNok("Soft card not connected")
        card = softCardDict[sim_router.MAIN_INTERFACE].simReader.getHandler().getCard(softCardDict[sim_router.MAIN_INTERFACE].index)
        card.satCtrl.satShell(param, value)
        return self.responseOk()

    ######################
    # Internal functions #
    ######################
    def updateInteractive(self, interactive):
        self.interactive = interactive

    def queryUser(self, question, default=''):
        "raw_input returns default value for enter"
        yes = set(['yes','y', 'ye'])
        change = set(['ne','new'])

        if default:
            choice = '[yes/no/new]: '
        else:
            choice = '[yes/no]: '

        choice = raw_input('\n' + question + '? ' + choice).lower()
        if choice in yes:
            if default:
                return default
            return True
        elif choice in change:
            if not default:
                return False
            return raw_input('Provide new value: ')
        else:
            return False

    def verifyCode(self, pinId):
        if pinId in [sim_codes.PIN_1, sim_codes.PIN_1_ENABLE, sim_codes.PIN_1_DISABLE]:
            attemptsMax = 3
            attemptsLeft = self.simCtrl.pin1Status()
            codeName = "PIN1"
        elif pinId == sim_codes.PIN_1_UNBLOCK:
            attemptsMax = 10
            attemptsLeft = self.simCtrl.pin1UnblockStatus()
            codeName = "PUK1"
        elif pinId == sim_codes.PIN_2:
            attemptsMax = 3
            attemptsLeft = self.simCtrl.pin2Status()
            codeName = "PIN2"
        elif pinId == sim_codes.PIN_2_UNBLOCK:
            attemptsMax = 10
            attemptsLeft = self.simCtrl.pin2UnblockStatus()
            codeName = "PUK2"
        elif pinId == sim_codes.ADM_1:
            attemptsMax = 3
            attemptsLeft = self.simCtrl.adm1Status()
            codeName = "ADM1"
        elif pinId == sim_codes.ADM_2:
            attemptsMax = 3
            attemptsLeft = self.simCtrl.adm2Status()
            codeName = "ADM2"
        elif pinId == sim_codes.ADM_4:
            attemptsMax = 3
            attemptsLeft = self.simCtrl.adm4Status()
            codeName = "ADM4"
        else:
            logging.error("PinId: %02X invalid" %pinId)
            return False

        if attemptsLeft == None:
            logging.error("Couldn't get attempts left")
            return False

        if attemptsLeft > attemptsMax:
            #ADM1 might have max attempts 10
            attemptsMax = 10

        if pinId not in [sim_codes.PIN_1_ENABLE, sim_codes.PIN_1_DISABLE]:
            code = sim_codes.defaultCard[pinId]
        else:
            code = sim_codes.defaultCard[sim_codes.PIN_1]

        if not self.forceCodes or attemptsLeft < attemptsMax:
            if not self.interactive:
                logging.warning("Security condition not satisfied, %s required. Attempts left: %d/%d. Default code:%s" %(codeName, attemptsLeft, attemptsMax, code))
                return None
            code = self.queryUser(("Security condition not satisfied, %s required. Attempts left: %d/%d.\nTry code %s=%s"
                                   %(codeName, attemptsLeft, attemptsMax, codeName, code)), code)
        if not code:
            return False
        return self.simCtrl.verifyCode(pinId, code)

    def updatePrompt(self):
        path = self.simCtrl.getCurrentFilePath()
        self.simCtrl.router.setShellPrompt('\n' + path + '>')

    def responseOk(self, out=None):
        name = traceback.extract_stack()[-2][2]
        logging.info("")
        logging.info("%s:" %(name))
        self.updatePrompt()
        if out:
            outValue = ("status OK", "data %s" %out)
        else:
            outValue = ("status OK", None)
        if not self.interactive:
            logging.info(outValue[0])
            if outValue[1]:
                logging.info(outValue[1])
        return outValue

    def responseNok(self, out=None):
        name = traceback.extract_stack()[-2][2]
        logging.info("")
        logging.info("%s:" %(name))
        self.updatePrompt()
        if out:
            outValue = ("status NOK", out)
        else:
            outValue = ("status NOK", None)
        if not self.interactive:
            logging.info(outValue[0])
            if outValue[1]:
                logging.info(outValue[1])
        return outValue

    def getValue(self, cmd):
        status, data = cmd
        if status:
            if data:
                return data.lstrip("data ")
            else:
                return True
        else:
            return None

    def getIntValue(self, cmd):
        value = self.getValue(cmd)
        if value:
            return int(value)
        else:
            return None

    def statusOk(self, status):
        expected = 'status OK'
        if status != expected:
            return False
        return True

    def assertOk(self, status, out=None):
        if not self.statusOk(status):
            str = status + " not expected"
            if out:
                str += ", info: " + out
            raise Exception(str)

    def assertNok(self, status, out=None):
        if self.statusOk(status):
            str = status + " not expected"
            if out:
                str += ", info: " + out
            raise Exception(str)

    def checkFileConditions(self, path, accessMode):
        "Check conditions for file"
        if self.simCtrl.router.simType == types.TYPE_USIM:
            arrRecord, arrValue = self.simCtrl.getArrRecordForFile(path)
            if not (arrValue and arrRecord):
                # Try with Expanded SE
                arrValue = self.simCtrl.getSecurityAttrib(path)
                if not arrValue:
                    return False
            conditions, condMode = types.getAccessConditions(arrValue, accessMode)
        else:
            conditions, condMode = self.simCtrl.getConditions(path, accessMode)
        if (types.AC_UNKNOWN or None) in conditions:
            logging.warning("UNKNOWN condition for file %s" %path)
            return False
        status = self.verifyConditions(conditions, condMode)
        return status

    def modifyArrConditions(self, arrPath, arrRecord, arrValue, accessMode):
        logging.debug("Setting desired access mode condition to ALWAYS")
        status = self.checkFileConditions(arrPath, types.AM_EF_UPDATE)
        if status:
            status = self.simCtrl.setArrCondition(arrPath, arrRecord, arrValue, accessMode, types.AC_ALWAYS)
        if not status:
            logging.warning("Couldn't update ARR file")
            return False
        return True

    def restoreArrConditions(self, arrPath, arrRecord, previousArrValue):
        logging.debug("Setting back conditions to previous values")
        status = self.simCtrl.setConditions(arrPath, arrRecord, previousArrValue)
        return status

    def restorePath(self, path):
        if self.simCtrl.getCurrentDirPath() != types.parentDirFromPath(path):
            # Select/Restore path
            sw1, sw2, data = self.simCtrl.selectFileByPath(path)
            if not data:
                return False
        return True

    def selectFile(self, path):
        sw1, sw2, data = self.simCtrl.selectFileByPath(path)
        if not data:
            logging.error("Failed to select: " + path)
            return False
        return True

    def getAbsolutePath(self, pathName):
        path = self.simCtrl.simFiles.parsePath(pathName)
        if not path:
            logging.error("path: %s not resolved" %pathName)
            return None
        if path == "/":
            return path

        absPath = ""
        tmpPath = ""
        currPath = self.simCtrl.getCurrentFilePath()
        currDirPath = self.simCtrl.getCurrentDirPath()
        if self.simCtrl.router.simType == types.TYPE_USIM:
            currAidId = self.simCtrl.getCurrentAidId()
        files = types.getFilesFromPath(path)
        for _file in files:
            pathFormat = types.getFileNameFormat(_file)
            if pathFormat == types.FILE_FORMAT_UNKNOWN:
                return None
            elif pathFormat == types.FILE_FORMAT_ID:
                if _file == "7FFF":
                    if currAidId == None:
                        return None
                    tmpPath = "ADF%d" %currAidId
                else:
                    tmpPath = _file
            elif pathFormat == types.FILE_FORMAT_NAME:
                fid = types.fidFromPath(self.simCtrl.simFiles.findFileByNameInDirs(_file))
                if not fid:
                    return None
                tmpPath = fid
            elif pathFormat == types.FILE_FORMAT_DF_CURRENT:
                tmpPath = currDirPath
                absPath = ""
            elif pathFormat == types.FILE_FORMAT_DF_PARENT:
                currPath = types.parentDirFromPath(currDirPath)
                currDirPath = currPath
                tmpPath = currPath
                absPath = ""
            elif pathFormat == types.FILE_FORMAT_ADF_ID:
                tmpPath = _file
            elif pathFormat == types.FILE_FORMAT_ADF_NAME:
                aidId = self.simCtrl.simFiles.getAdfId(_file)
                if aidId == None:
                    return None
                tmpPath = aidId
            else:
                raise Exception("Format: %d not expected" %fileFormat)
            if types.fidFromPath(absPath) != tmpPath:
                absPath = types.addToPath(absPath, tmpPath)
        if absPath[0] != "/":
            absPath = "/" + absPath
        return absPath

    def verifyCondition(self, condition):
        if condition == types.AC_ALWAYS:
            return True
        elif condition == types.AC_NEVER:
            logging.error("Never condition")
            return False
        elif condition == types.AC_CHV1:
            if self.simCtrl.pin1Verified():
                return True
            pinId = sim_codes.PIN_1
        elif condition == types.AC_CHV2:
            pinId = sim_codes.PIN_2
        elif condition == types.AC_ADM1:
            pinId = sim_codes.ADM_1
        elif condition == types.AC_ADM2:
            pinId = sim_codes.ADM_2
        elif condition == types.AC_ADM3:
            pinId = sim_codes.ADM_3
        elif condition == types.AC_ADM4:
            pinId = sim_codes.ADM_4
        elif condition == types.AC_ADM5:
            pinId = sim_codes.ADM_5
        else:
            logging.error("Unknown condition: %d" %condition)
            return False
        return self.verifyCode(pinId)

    def verifyConditions(self, conditions, mode):
        for condition in conditions:
            status = self.verifyCondition(condition)
            if mode == None:
                return status
            if mode == types.SC_DO_OR_TEMPLATE_TAG:
                if status:
                    return True
            elif mode == types.SC_DO_AND_TEMPLATE_TAG:
                if not status:
                    return False
            elif mode == types.SC_DO_NOT_TEMPLATE_TAG:
                if status:
                    return False
        return status

    def deleteRaw(self, path, accessMode=types.AM_EF_DELETE):
        "Delete file"
        status = False
        with FileAccessCondition(self, path, accessMode) as conditionStatus:
            if not conditionStatus:
                return False
            status = self.simCtrl.deleteFile(path)
            if not status:
                return status

        if types.fidFromPath(path).startswith("ADF"):
            efDirPath = "/2F00"
            with FileAccessCondition(self, efDirPath, types.AM_EF_RESIZE) as efDirConditionStatus:
                if not efDirConditionStatus:
                    return False
                status = self.simCtrl.removeApplication(types.getAdfId(path))
        return status


    def readRaw(self, path, forceAccess=False):
        with FileAccessCondition(self, path, types.AM_EF_READ, forceAccess) as conditionStatus:
            if not conditionStatus:
                return None
            data = self.simCtrl.readFileData(path)
        return data


    def writeRaw(self, path, data):
        status = False
        with FileAccessCondition(self, path, types.AM_EF_UPDATE) as conditionStatus:
            if not conditionStatus:
                return False
            status = self.simCtrl.writeFileData(path, data)
        return status

    def resizeRaw(self, path, newFileSize, fillPattern):
        if newFileSize:
            fileSize = int(newFileSize, 16)
        else:
            return False
        pattern = None
        if fillPattern:
            pattern = bytearray.fromhex(fillPattern)

        status = False
        with FileAccessCondition(self, path, types.AM_EF_RESIZE) as conditionStatus:
            if not conditionStatus:
                return False
            status = self.simCtrl.resizeFile(path, fileSize, pattern)
        return status


    def extendRaw(self, path, sizeToExtend):
        if sizeToExtend:
            sizeToExtend = int(sizeToExtend)
        else:
            return False
        status = False
        with FileAccessCondition(self, path, types.AM_EF_RESIZE) as conditionStatus:
            if not conditionStatus:
                return False
            status = self.simCtrl.extendFile(path, sizeToExtend)
        return status


    def createRaw(self, path, fileParam):
        "Create files and directories"
        filePath = self.getAbsolutePath(path)
        files = types.getFilesFromPath(filePath)
        numOfFiles = len(files)
        # Check if max DF level is not exceeded
        if numOfFiles > 5:
            raise Exception("Max DF level exceeded.")
        last = numOfFiles - 1
        filePath = ""
        for i, file in enumerate(files):
            filePath += "/" + file
            if self.selectFile(filePath):
                logging.debug("File %s selected" %filePath)
                if i == last:
                    logging.error("File already exists")
                    return False
                continue
            if i == last and path[-1] != '/':
                # Create EF.
                # Last file without '/' at the end.
                logging.info("Creating file: %s" %filePath)
                status = self.createFile(filePath, fileParam)
            else:
                # Create DF or ADF.
                # If it's not last element, it must be a directory!
                logging.info("Creating directory: %s" %filePath)
                status = self.createDirectory(filePath, fileParam)
                if not status:
                    return False
                # Create an Arr file in the new created directory.
                arrFile = "%s/%04X" %(filePath, types.EF_ARR)
                status = self.createArr(arrFile, fileParam=None)
            if not status:
                return False
        return True

    def createFile(self, path, fileParam=None):
        logging.debug("Create file: %s" %path)
        #Default file param value
        shareable = True
        fileType = types_g.fileDescriptor.TRANSPARENT_STRUCTURE
        fileSize = 0x20
        recordLength = 0x20
        LcsiValue = 0x5
        se01 = 0x04
        sfi = 0x0

        if fileParam:
            #parse file parameter value provided in SIM shell
            value = types.getParamValue(fileParam, "shareable")
            if value:
                shareable = int(value, 16)
            value = types.getParamValue(fileParam, "fileType")
            if value:
                fileType = int(value, 16)
            value = types.getParamValue(fileParam, "fileSize")
            if value:
                fileSize = int(value, 16)
            if fileType == types_g.fileDescriptor.TRANSPARENT_STRUCTURE:
                recordLength = 0x00
            else:
                value = types.getParamValue(fileParam, "recordLength")
                if value:
                    recordLength = int(value, 16)
            value = types.getParamValue(fileParam, "LcsiValue")
            if value:
                LcsiValue = int(value, 16)
            value = types.getParamValue(fileParam, "se01")
            if value:
                se01 = int(value, 16)
            value = types.getParamValue(fileParam, "sfi")
            if value:
                sfi = int(value, 16)

        parentPath = types.parentDirFromPath(path)
        status = False
        with FileAccessCondition(self, parentPath, types.AM_DF_CREATE_FILE_EF) as conditionStatus:
            if not conditionStatus:
                return False

            status = self.simCtrl.createFile(path,
                                    shareable,
                                    fileType,
                                    fileSize,
                                    recordLength,
                                    LcsiValue,
                                    se01,
                                    sfi)
        return status

    def createDirectory(self, path, fileParam=None):
        logging.debug("Create directory: %s" %path)
        #Default file param value
        shareable = True
        totalFileSize = 0x64
        LcsiValue = 0x5
        se01 = 0x04
        sfi = 0x0
        aid = types.DEFAULT_APP_AID

        if fileParam:
            #parse file parameter value provided in SIM shell
            value = types.getParamValue(fileParam, "shareable")
            if value:
                shareable = int(value, 16)
            value = types.getParamValue(fileParam, "totalFileSize")
            if value:
                totalFileSize = int(value, 16)
            value = types.getParamValue(fileParam, "LcsiValue")
            if value:
                LcsiValue = int(value, 16)
            value = types.getParamValue(fileParam, "se01")
            if value:
                se01 = int(value, 16)
            value = types.getParamValue(fileParam, "sfi")
            if value:
                sfi = int(value, 16)
            value = types.getParamValue(fileParam, "aid")
            if value:
                aid = bytearray.fromhex(value)

        parentPath = types.parentDirFromPath(path)
        status = False
        with FileAccessCondition(self, parentPath, types.AM_DF_CREATE_FILE_DF) as conditionStatus:
            if not conditionStatus:
                return False
            status = self.simCtrl.createDirectory(path,
                                                shareable,
                                                LcsiValue,
                                                se01,
                                                totalFileSize,
                                                aid)
            if not status:
                return False

        if types.fidFromPath(path).startswith("ADF"):
            efDirPath = "/2F00"
            with FileAccessCondition(self, efDirPath, types.AM_EF_RESIZE) as efDirConditionStatus:
                if not efDirConditionStatus:
                    return False
                status = self.simCtrl.addApplication(types.getAdfId(path), aid)
        return status

    def createArr(self, path, fileParam):
        logging.debug("Create EF_ARR file: %s" %path)
        #Default file param value
        shareable = True
        LcsiValue = 0x5
        nbrOfRecords = 0x09
        recordSize = 0x60
        if fileParam:
            #parse file parameter value provided in SIM shell
            value = types.getParamValue(fileParam, "shareable")
            if value:
                shareable = int(value, 16)
            value = types.getParamValue(fileParam, "LcsiValue")
            if value:
                LcsiValue = int(value, 16)
            value = types.getParamValue(fileParam, "nbrOfRecords")
            if value:
                nbrOfRecords = int(value, 16)
            value = types.getParamValue(fileParam, "recordSize")
            if value:
                recordSize = int(value, 16)

        parentPath = types.parentDirFromPath(path)
        if not parentPath:
            parentPath = "/7FFF"
        status = False
        with FileAccessCondition(self, parentPath, types.AM_DF_CREATE_FILE_EF) as conditionStatus:
            if not conditionStatus:
                return False
            status, sw = self.simCtrl.createArrFile(path,
                                                types.ARR_CUSTOM, #types.ARR_ALL_ALWAYS
                                                shareable=True,
                                                LcsiValue=0x05,
                                                nbrOfRecords=0x09,
                                                recordSize=0x60)
            if not status and sw == types_g.sw.INCORRECT_PARAMETER_IN_DATA_FIELD:
                # Try once again with a different security type.
                # Sim cards may support different security for creating Arr file
                status, sw = self.simCtrl.createArrFile(path,
                                                    types.ARR_CUSTOM, #types.ARR_ALL_ALWAYS
                                                    shareable=True,
                                                    LcsiValue=0x05,
                                                    nbrOfRecords=0x09,
                                                    recordSize=0x60,
                                                    securityType=types.SECURITY_ATTRIB_COMPACT_TAG)
            elif not status and sw == types_g.sw.WRONG_PARAMETERS_P1_P2:
                # For Gemalto Sim cards
                status, sw = self.simCtrl.createArrFile(path,
                                                    types.ARR_CUSTOM, #types.ARR_ALL_ALWAYS
                                                    shareable=True,
                                                    LcsiValue=0x05,
                                                    nbrOfRecords=0x09,
                                                    recordSize=0x60,
                                                    securityType=types.SECURITY_ATTRIB_COMPACT_TAG,
                                                    se01ValueTag=types.EFARR_ACCESS_RULE_SE01_TAG)
        return status

    def _backup(self, path, node):
        if path[-1] != "/":
            path += "/"
        filesToCheck = self.simCtrl.simFiles.findAllChildFiles(path)
        for file in filesToCheck:
            fid =  types.fidFromPath(file)
            format = types.getFileNameFormat(file)
            if format == types.FILE_FORMAT_ADF_NAME:
                fid = self.simCtrl.simFiles.getAdfId(fid)
                if not fid:
                    continue
                aidId = int(fid.replace("ADF",""))
                sw2 = self.simCtrl.selectAid(aidId=aidId)
                if not sw2:
                    logging.info("Failed to select AID: " + fid)
                    continue
            else:
                sw1, sw2, data = self.simCtrl.selectFile(fid)
                if sw1 != types_g.sw1.RESPONSE_DATA_AVAILABLE_3G:
                    logging.info("Failed to select: " + fid)
                    continue
            sw1, sw2, data = self.simCtrl.getResponse(sw2)
            pathTmp = self.simCtrl.getCurrentFilePath()
            if file[-1] != "/":
                fileValue = self.readRaw(pathTmp, forceAccess=True)
                if not fileValue:
                    continue
                self.simBackup.addEf(node, file, fileValue.replace(";",""), data)
            else:
                if format == types.FILE_FORMAT_ADF_NAME:
                    aid = hextools.bytes2hex(types.getAidFromData(data), separator="")
                    nodeTmp = self.simBackup.addAdf(node, fid, aid, data)
                else:
                    nodeTmp = self.simBackup.addDf(node, fid, data)
                self._backup(pathTmp, nodeTmp)
                #restore previous path
                sw1, sw2, data = self.simCtrl.selectFileByPath(path)
                if types.assertSw(sw1, sw2, checkSw='NO_ERROR'):
                    raise Exception("Failed to select current dir")
        return True

class FileAccessCondition(object):
    def __init__(self, ss, path, accessMode, forceAccess=True):
        self.ss = ss
        self.status = False
        self.restoreCondition = False
        self.savedPath = self.ss.simCtrl.getCurrentFilePath()
        self.status = self.ss.checkFileConditions(path, accessMode)
        if not self.status and forceAccess:
            # Get Arr record number and its value.
            self.arrRecord, arrValue = self.ss.simCtrl.getArrRecordForFile(path)
            if not (self.arrRecord and arrValue):
                return
            # Current file is pointing at Arr file.
            self.arrFilePath = self.ss.simCtrl.getCurrentFilePath()
            self.previousArrValue = arrValue[:] # make a copy
            self.status = self.ss.modifyArrConditions(self.arrFilePath, self.arrRecord, arrValue, accessMode)
            if self.status:
                self.restoreCondition = True
    def __enter__(self):
        self.ss.restorePath(self.savedPath)
        return self.status
    def __exit__(self, type, value, traceback):
        if self.restoreCondition:
            savedPath = self.ss.simCtrl.getCurrentFilePath()
            self.ss.restoreArrConditions(self.arrFilePath, self.arrRecord, self.previousArrValue)
            self.ss.restorePath(savedPath)
