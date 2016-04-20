#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging
from lxml import etree
import shutil

from util import types
from util import hextools

PIN_1 = "1111"
PIN_1_ATTEMPTS = "3"
PIN_1_UNBLOCK = "11111111"
PIN_1_UNBLOCK_ATTEMPTS = "10"

PIN_2 = "2222"
PIN_2_ATTEMPTS = "3"
PIN_2_UNBLOCK = "22222222"
PIN_2_UNBLOCK_ATTEMPTS = "10"

ADM_1 = "ADM11111"
ADM_1_ATTEMPTS = "3"

CODE_ENABLED = "1"
CODE_VERIFIED = "1"
CODE_NOT_VERIFIED = "0"

__version__ = "1.0"

def getParamValue(paramStr, paramName):
    params = paramStr.split(', ')

    for param in params:
        paramList = param.split(':')
        if paramList[0] == paramName:
            return paramList[1]
    return None

def getIntParamValue(paramStr, paramName):
    value = getParamValue(paramStr, paramName)
    if value:
        value = int(value)
    return value

def createFileNode(root, tag, id):
    node = etree.SubElement(root, "node")
    node.tag = tag
    node.attrib['id'] = id
    return node

def addFileAttribute(node, attr, value):
    nodeId = etree.SubElement(node, attr)
    nodeId.text = value

def bytesToXmlValue(bytes):
    return ''.join(format(bytes[x], '02X') for x in range(0, len(bytes)))

def xmlValueToBytes(value):
    # reads hex strings with or without space separator
    return bytearray.fromhex(value)

def addAtr(currentNode, atr):
    node = etree.SubElement(currentNode, "atr")
    node.text = atr
    return node

def addMfNode(currentNode, arr_id, arr_rule):
    node = createFileNode(currentNode, 'mf', "3F00")
    addFileAttribute(node, "sfi", "")
    addFileAttribute(node, "arr_id", arr_id)
    addFileAttribute(node, "arr_rule", arr_rule)
    return node

def addDfNode(currentNode, id, arr_id, arr_rule):
    node = createFileNode(currentNode, 'df', id)
    addFileAttribute(node, "sfi", "")
    addFileAttribute(node, "arr_id", arr_id)
    addFileAttribute(node, "arr_rule", arr_rule)
    return node

def addAdfNode(currentNode, id, aid, arr_id, arr_rule):
    node = createFileNode(currentNode, 'df', id)
    addFileAttribute(node, "aid", aid)
    addFileAttribute(node, "sfi", "")
    addFileAttribute(node, "arr_id", arr_id)
    addFileAttribute(node, "arr_rule", arr_rule)
    return node

def addEfNode(currentNode, id, sfi, struct, size, record_len, value,
              arr_id, arr_rule, invalidated, rw_invalidated):
    node = createFileNode(currentNode, 'ef', id)
    addFileAttribute(node, "sfi", sfi)
    addFileAttribute(node, "struct", struct)
    addFileAttribute(node, "size", size)
    if record_len == None:
        record_len = "0"
    addFileAttribute(node, "record_len", record_len)
    addFileAttribute(node, "value", value)
    addFileAttribute(node, "arr_id", arr_id)
    addFileAttribute(node, "arr_rule", arr_rule)
    addFileAttribute(node, "invalidated", invalidated)
    addFileAttribute(node, "rw_invalidated", rw_invalidated)
    return node

def configureChvs(etree, root):
    nodeChv = etree.SubElement(root, "chv")

    nodeChv1 = etree.SubElement(nodeChv, "chv1")
    node = etree.SubElement(nodeChv1, "value")
    node.text = PIN_1
    node = etree.SubElement(nodeChv1, "enabled")
    node.text = CODE_ENABLED
    node = etree.SubElement(nodeChv1, "verified")
    node.text = CODE_NOT_VERIFIED
    node = etree.SubElement(nodeChv1, "attempts")
    node.text = PIN_1_ATTEMPTS
    node = etree.SubElement(nodeChv1, "attempts_left")
    node.text = PIN_1_ATTEMPTS

    nodeChv1Unblock = etree.SubElement(nodeChv, "chv1_unblock")
    node = etree.SubElement(nodeChv1Unblock, "value")
    node.text = PIN_1_UNBLOCK
    node = etree.SubElement(nodeChv1Unblock, "attempts")
    node.text = PIN_1_UNBLOCK_ATTEMPTS
    node = etree.SubElement(nodeChv1Unblock, "attempts_left")
    node.text = PIN_1_UNBLOCK_ATTEMPTS

    nodeChv2 = etree.SubElement(nodeChv, "chv2")
    node = etree.SubElement(nodeChv2, "value")
    node.text = PIN_2
    node = etree.SubElement(nodeChv2, "enabled")
    node.text = CODE_ENABLED
    node = etree.SubElement(nodeChv2, "verified")
    node.text = CODE_NOT_VERIFIED
    node = etree.SubElement(nodeChv2, "attempts")
    node.text = PIN_2_ATTEMPTS
    node = etree.SubElement(nodeChv2, "attempts_left")
    node.text = PIN_2_ATTEMPTS

    nodeChv2Unblock = etree.SubElement(nodeChv, "chv2_unblock")
    node = etree.SubElement(nodeChv2Unblock, "value")
    node.text = PIN_2_UNBLOCK
    node = etree.SubElement(nodeChv2Unblock, "attempts")
    node.text = PIN_2_UNBLOCK_ATTEMPTS
    node = etree.SubElement(nodeChv2Unblock, "attempts_left")
    node.text = PIN_2_UNBLOCK_ATTEMPTS

    nodeAdm1 = etree.SubElement(nodeChv, "adm1")
    node = etree.SubElement(nodeAdm1, "value")
    node.text = ADM_1
    node = etree.SubElement(nodeAdm1, "enabled")
    node.text = CODE_ENABLED
    node = etree.SubElement(nodeAdm1, "verified")
    node.text = CODE_NOT_VERIFIED
    node = etree.SubElement(nodeAdm1, "attempts")
    node.text = ADM_1_ATTEMPTS
    node = etree.SubElement(nodeAdm1, "attempts_left")
    node.text = ADM_1_ATTEMPTS

def xmlInit(atr):
    # Configure one attribute with set()
    root = etree.Element('sim_soft')
    root.set('version', __version__)
    addAtr(root, atr)
    configureChvs(etree, root)
    return root

def writeXml(simXmlFile, root):
    tree = etree.ElementTree(root)
    xml_document = etree.tostring(tree,
                                  pretty_print=True,
                                  xml_declaration=True,
                                  encoding='utf-8')

    file = open(simXmlFile, mode="w")
    file.write(xml_document)
    file.close()

def readXml(file):
    tree = etree.ElementTree()
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.parse(file, parser).getroot()
    return root

class SimXml(object):
    def __init__(self, file):
        self.file = file
        createXml = not os.path.exists(self.file)
        if createXml:
            origFile = self.file + ".bak"
            if not os.path.exists(origFile):
                raise Exception("Default xml file: %s not found" %origFile)
            shutil.copy2(origFile, file)
            logging.info("Default xml file restored")
        self.root = readXml(file)
        self.reset()

    def reset(self):
        self.SetChvNotVerified()

    def getApplications(self):
        # Read all AIDs from EF_DIR
        aidList = []
        efDir = self.getEfDir()
        numOfRecords = self.getFileNumberOfRecords(efDir)
        for idx in range(numOfRecords):
            record = self.getFileRecord(efDir, idx + 1)
            aid = types.getAidFromDirRecord(record)
            if aid:
                aidList.append(aid)
        return aidList

    def getAtr(self):
        return self.getBinaryFromText(self.root.find("./atr"))

    def getParentDir(self, dir):
        return dir.replace("/%s" %dir.split("/")[-1], "")

    def get(self, node, name):
        subNode = node.find(name)
        if subNode == None:
            raise Exception("%s has no '%s' node" %(node.attrib['id'], name))
        return subNode.text

    def getInt(self, node, name):
        try:
            return int(self.get(node, name))
        except:
            pass

    def getValue(self, node):
        return self.get(node, "value")

    def set(self, node, name, text, save=True):
        subNode = node.find(name)
        subNode.text = text
        if save:
            writeXml(self.file, self.root)

    def setValue(self, node, text):
        self.set(node, "value", text)

    def getBinaryValue(self, file):
        hexStr = self.getValue(file)
        return hextools.hex2bytes(hexStr.replace(" ", "").replace("\n", ""))

    def setBinaryValue(self, file, data):
        value = hextools.bytes2hex(data)
        #value = bytesToXmlValue(data)
        self.setValue(file, value)

    def getBinaryFromText(self, node):
        return hextools.hex2bytes(node.text.replace(" ", ""))

    def getFileType(self, file):
        typeStr = file.tag
        if typeStr == "mf":
            type = types.FILE_TYPE_MF
        elif typeStr == "df":
            type = types.FILE_TYPE_DF
        elif typeStr == "ef":
            type = types.FILE_TYPE_EF
        else:
            raise Exception("Unknown file type")
        return type

    def getEfDir(self):
        return self.root.find("./mf/ef[@id='2F00']")

    def getFileAid(self, file):
        if self.getFileType(file) != types.FILE_TYPE_DF:
            raise Exception("Expecting DF")
        return self.get(file, "aid")

    def setFileAid(self, file, aid):
        if self.getFileType(file) != types.FILE_TYPE_DF:
            raise Exception("Expecting DF")
        self.set(file, "aid", aid, save="False")

    def getFileId(self, file):
        return file.attrib['id']

    def getFileStruct(self, file):
        if self.getFileType(file) != types.FILE_TYPE_EF:
            raise Exception("Expecting EF")
        return self.getInt(file, "struct")

    def getFileSize(self, file):
        if self.getFileType(file) != types.FILE_TYPE_EF:
            raise Exception("Expecting EF")
        return self.getInt(file, "size")

    def setFileSize(self, file, size):
        if self.getFileType(file) != types.FILE_TYPE_EF:
            raise Exception("Expecting EF")
        self.set(file, "size", size)

    def getPathFromFile(self, file):
        if file == None:
            return
        pathXml = etree.ElementTree(self.root).getpath(file)
        pathXml = pathXml.split("mf")[1]
        path = "./mf[@id='3F00']"
        for _file in pathXml.split('/'):
            if not _file:
                #path = types.addToPath(path, "/")
                continue
            absPath = types.addToPath(path, _file)
            id = etree.ElementTree(self.root).xpath(absPath)[0].attrib['id']
            #"./mf/df[@id='ADF0']"
            fileId = "%s[@id='%s']" %(_file.split('[')[0], id)
            path = types.addToPath(path, fileId)
        return path

    def findFileInParrent(self, dir, id):
        #Search recursively until an ADF or the MF is reached.
        while 1:
            file = self.findFileInDir(dir, id)
            if file !=  None:
                return file
            fid = types.fidFromPath(dir)
            # FIXME: in the current implementation ADF is a child of the MF
            if "mf" in fid: # or "ADF" in fid:
                return None
            dir = self.getParentDir(dir)

    def findFileInDir(self, dir, id):
        if id != "3F00":
            path = dir + "/*[@id='" + id + "']"
        else:
            path = "./mf"
        return self.root.find(path)

    def findAdf(self, aid):
        aidValue = bytesToXmlValue(aid)
        path = "./mf/*[aid='" + aidValue + "']"
        return self.root.find(path)

    def findFile(self, path):
        if path != None:
            return self.root.find(path)
        else:
            return None

    def countChildDf(self, dir):
        #dir = self.currentDir

        filePath = "%s/df" %dir
        files = self.root.findall(filePath)

        if not files:
            return 0
        else:
            return len(files)

    def countChildEf(self, dir):
        #dir = self.currentDir

        filePath = "%s/ef" %dir
        files = self.root.findall(filePath)

        if not files:
            return 0
        else:
            return len(files)

    def getFileRecord(self, file, record):
        recordLength = self.getFileRecordLength(file)
        if not recordLength:
            return []
        fileSize = self.getFileSize(file)
        value = self.getBinaryValue(file)
        start = (record-1) * recordLength
        end = start + recordLength
        return value[start:end]

    def updateFileRecord(self, file, record, data):
        recordLength = self.getFileRecordLength(file)
        fileSize = self.getFileSize(file)
        value = self.getBinaryValue(file)
        start = (record-1) * recordLength
        end = start + len(data)
        value[start:end] = data
        self.setBinaryValue(file, value)


    def getFileRecordLength(self, file):
        if self.getFileType(file) != types.FILE_TYPE_EF:
            raise Exception("Expecting EF")
        if self.getFileStruct(file) == types.FILE_STRUCTURE_TRANSPARENT:
            logging.warning("Record not available for transparent EF")
            return None
        return self.getInt(file, "record_len")

    def getFileNumberOfRecords(self, file):
        recordLength = self.getFileRecordLength(file)
        fileSize = self.getFileSize(file)
        numOfRecords = fileSize / recordLength
        return numOfRecords

    def getChv(self, chv):
        chvPath = "./chv/"
        chvX = self.root.find(chvPath + chv)
        if chvX == None:
            raise Exception("Incorrect CHV:%s" %chv)
        return chvX

    def getNumberOfChv(self):
        chvPath = "./chv"
        NbrOfChild = 0
        root = self.root.find(chvPath)
        for child in root:
            NbrOfChild += 1
        return NbrOfChild

    def SetChvNotVerified(self):
        chvPath = "./chv"
        root = self.root.find(chvPath)
        for child in root:
            if "unblock" not in child.tag:
                self.set(child, "verified", "0")

    def getValueChv(self, chv):
        return self.getValue(self.getChv(chv))

    def setValueChv(self, chv, value):
        self.setValue(self.getChv(chv), value)

    def enabledChv(self, chv):
        return self.getInt(self.getChv(chv), "enabled")

    def setEnabledChv(self,chv, state):
        self.set(self.getChv(chv), "enabled", str(state))

    def verifiedChv(self,chv):
        return self.getInt(self.getChv(chv), "verified")

    def setVerifiedChv(self, chv, state):
        self.set(self.getChv(chv), "verified", str(state), save=False)

    def remaningAttemptsChv(self, chv):
        return self.getInt(self.getChv(chv), "attempts_left")

    def resetAttemptsChv(self, chv):
        attemptsMax = self.getInt(self.getChv(chv), "attempts")
        self.set(self.getChv(chv), "attempts_left", str(attemptsMax))

    def decrementRemaningAttemptsChv(self, chv):
        attempts = self.getInt(self.getChv(chv), "attempts_left")
        if attempts:
            self.set(self.getChv(chv), "attempts_left", str(attempts - 1))

    def getEfArr(self, dir, id):
        file = self.findFileInParrent(dir, id)
        if file == None:
            raise Exception("EF_ARR %s not found" %id)
        return file

    def getEfArrRuleValue(self, file, ruleId):
        value = self.getFileRecord(file, ruleId)
        return value

    def findEfArr(self, file):
        arrId = self.get(file, "arr_id")
        arrRule = self.getInt(file, "arr_rule")
        return arrId, arrRule

    def isFileEnabled(self, file):
        return not self.getInt(file, "invalidated")

    def setFileEnabled(self, file):
        self.set(file, "invalidated", "0")

    def setFileDisabled(self, file):
        self.set(file, "invalidated", "1")

    def createDirectory(self, path, fid, arrId, arrRule, aid=None):
        parentNode = self.root.find(path)

        node = createFileNode(parentNode, 'df', "%X" % fid)

        addFileAttribute(node, "sfi", "")
        addFileAttribute(node, "arr_id", "%X" % arrId)
        addFileAttribute(node, "arr_rule", str(arrRule))
        if aid != None:
            aidValue = bytesToXmlValue(aid)
            addFileAttribute(node, "aid", aidValue)

        writeXml(self.file, self.root)
        return node

    def createFile(self, path, fid, struct, size, recordLen, arrId, arrRule, data=[]):
        parentNode = self.root.find(path)
        node = createFileNode(parentNode, 'ef', "%X" % fid)

        addFileAttribute(node, "sfi", "")
        addFileAttribute(node, "struct", str(struct))
        addFileAttribute(node, "size", str(size))
        if recordLen != 0:
            addFileAttribute(node, "record_len", str(recordLen))
        addFileAttribute(node, "arr_id", "%X" % arrId)
        addFileAttribute(node, "arr_rule", str(arrRule))
        #hardcoded, by default not invalidated
        addFileAttribute(node, "invalidated", "0")
        addFileAttribute(node, "rw_invalidated", "0")

        value = bytesToXmlValue(data)
        if size > len(data):
            value += ' '
        # fill with 'FF' len(data)
        value += bytesToXmlValue([0xFF] * (size - len(data)))
        addFileAttribute(node, "value", value)

        writeXml(self.file, self.root)
        return node

    def deleteFile(self, file):
        file.getparent().remove(file)
        writeXml(self.file, self.root)

    def resizeFile(self, file, size, data):
        value = self.getBinaryValue(file)
        currentSize = len(value)
        if currentSize == size:
            return
        if  size < currentSize:
            self.setBinaryValue(file, value[:size])
        else:
            if data:
                struct = self.getFileStruct(file)
                if struct != types.FILE_STRUCTURE_TRANSPARENT:
                    while len(value) < size:
                        value += data
                        recordLength = self.getFileRecordLength(file)
                        if len(data) < recordLength:
                            # fill with the value of the last byte
                            value += [data[-1]] * (size - len(value))
                else:
                    value += data
                    # fill with the value of the last byte
                    value += [data[-1]] * (size - len(value))
            else:
                # fill with 0xFF
                value += [0xFF] * (size - len(value))
            self.setBinaryValue(file, value[:size])

        self.setFileSize(file, str(size))
        writeXml(self.file, self.root)
