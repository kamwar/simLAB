#!/usr/bin/python
# LICENSE: GPL2
# (c) 2016 Kamil Wartanowicz

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import logging
from lxml import etree
import re

from util import types
from util import types_g


class SimFiles(object):
    def __init__(self, type):
        self.simType = type
        self.simXml = SimFilesXml(self.simType)
        self.adfs = None
        self.currentDirPath = "/"

    def resolveAdfs(self, efDirData):
        adfs = {}
        if self.simType == types.TYPE_SIM:
            return adfs
        if not efDirData:
            logging.warning("EF_DIR data is empty")
            return adfs
        efDirRecords = efDirData.split(';')
        usimAdfId = self.getAdfIdFromRecords(types_g.adfName.ADF_USIM, efDirRecords)
        if usimAdfId:
            adfs.update({usimAdfId : types_g.adfName[types_g.adfName.ADF_USIM]})
        isimAdfId = self.getAdfIdFromRecords(types_g.adfName.ADF_ISIM, efDirRecords)
        if isimAdfId:
            adfs.update({isimAdfId : types_g.adfName[types_g.adfName.ADF_ISIM]})
        self.adfs = adfs

    def getCurrentDirPath(self):
        return self.currentDirPath

    def setCurrentDirPath(self, currentDir):
        self.currentDirPath = currentDir

    def getAdfIdFromRecords(self, adf, efDirRecords):
        for idx, aid in enumerate(efDirRecords):
            if aid[8:22] == "A00000008710%.2X" %adf:
                return "ADF%d" %idx
        return None

    def checkAdfs(self):
        #if not self.adfs:
        #    self.resolveAdfs()
        if not self.adfs:
            logging.warning("No adfs found")
            return False
        return True

    def getAdfId(self, adfName):
        if not self.checkAdfs():
            return None
        try:
            return types.getKeyFromDictValue(self.adfs, adfName)
        except:
            logging.warning("%s does not exist" %adfName)
            return None

    def getAdfName(self, adfId):
        if not self.checkAdfs():
            return None
        if adfId in self.adfs.keys():
            return self.adfs[adfId]
        else:
            return None

    def getDirsToSearch(self):
        #Return directories with priority to search file
        if self.simType == types.TYPE_USIM:
            dirs = ["/ADF_USIM/",
                    "/ADF_ISIM/",
                    "/7F10/",
                    "/7F20/",
                    "/",]
        else:
            dirs = ["/7F20/",
                    "/7F10/",
                    "/",]
        return dirs

    def getPathFromRawPath(self, rawPath):
        dir = types.parentDirFromPath(rawPath)
        name = types.fidFromPath(rawPath)
        format = types.getFileNameFormat(name)
        if format not in [types.FILE_FORMAT_NAME,
                          types.FILE_FORMAT_ID,
                          types.FILE_FORMAT_ADF_NAME]:
            return rawPath
        if dir and not dir == "../":
            if format == types.FILE_FORMAT_ID:
                 return rawPath
            node, xmlPath = self.findFileByName(dir, name)
            if node == None:
                logging.warning("Name: %s not resolved" %name)
                return None
            return self.simXml.getPathFromXml(xmlPath)
        else:
             if format == types.FILE_FORMAT_NAME:
                path = self.findFileByNameInDirs(rawPath)
             elif format == types.FILE_FORMAT_ID:
                path = self.findFileByIdInDirs(rawPath)
             return path

    def findFileByNameInDirs(self, name):
        dirs = self.getDirsToSearch()
        for dir in dirs:
            node, xmlPath = self.findFileByName(dir, name)
            if node != None:
                break
        if node == None:
            logging.warning("Name: %s not resolved" %name)
            return None
        return self.simXml.getPathFromXml(xmlPath)

    def findFileByIdInDirs(self, id):
        dirs = self.getDirsToSearch()
        for dir in dirs:
            node, xmlPath = self.findFileById(dir, id)
            if node != None:
                break
        if node == None:
            logging.warning("Name: %s not resolved" %id)
            return None
        return self.simXml.getPathFromXml(xmlPath)

    def parsePath(self, path):
        path = path.upper()
        format = types.getFileNameFormat(path)
        if format in [types.FILE_FORMAT_PATH_ABSOLUTE,
                      types.FILE_FORMAT_DF_CURRENT,
                      types.FILE_FORMAT_DF_PARENT]:
            absPath = path
        elif format in [types.FILE_FORMAT_ADF_ID, types.FILE_FORMAT_ADF_NAME]:
            absPath = types.addToPath("/", path)
        elif path == '/':
            absPath = "/"
        elif format in [types.FILE_FORMAT_NAME, types.FILE_FORMAT_ID]:
            head = path.split("/")[0]
            tail = "/".join(path.split("/")[1:])
            fid = self.getPathFromRawPath(head)
            if not fid:
                return None
            absPath = types.addToPath(fid, tail)
        elif format == types.FILE_FORMAT_UNKNOWN:
            return None
        else:
            raise Exception("Format:%d not expected" %format)
        return absPath

    def getFilePath(self, pathName):
        path = ""
        pathFormat = types.getFileNameFormat(pathName)
        if pathFormat == types.FILE_FORMAT_DF_CURRENT:
            pathName = types.addToPath(self.getCurrentDirPath(), pathName.lstrip("."))
        elif pathFormat == types.FILE_FORMAT_DF_PARENT:
            parentPath = types.parentDirFromPath(self.getCurrentDirPath())
            pathName = "%s%s" %(parentPath, pathName.lstrip(".."))
        elif pathName in [types.FILE_FORMAT_ID,
                          types.FILE_FORMAT_NAME,
                          types.FILE_FORMAT_ADF_ID,
                          types.FILE_FORMAT_ADF_NAME]:
            pathName = self.getAbosulteFilePath(pathName)

        files = pathName.split("/")
        for i, _file in enumerate(files):
            if not _file:
                path = types.addToPath(path, "/")
                continue
            fileFormat = types.getFileNameFormat(_file)
            if fileFormat == types.FILE_FORMAT_ADF_ID:
                _file = self.getAdfName(_file)
                if not _file:
                    logging.warning("Could not get ADF Name from path: %s" %pathName)
                    return None
            path = types.addToPath(path, _file)
        return path

    def findAllChildFiles(self, path):
        files = []
        path = self.getFilePath(path)
        if not path:
            return files
        xmlPath = self.simXml.getXmlPath(path)
        nodes = self.simXml.root.findall(xmlPath)
        if not nodes:
            return files
        nodes = nodes[0]

        for node in nodes:
            try:
                nodeId = node.attrib['id']
                if node.tag == "df":
                    nodeId += "/"
                files.append(nodeId)
            except:
                #not every node has id, e.g. <name>ADF_ISIM</name>
                continue
        return files

    def findFileByName(self, path, name):
        root, _xmlPath = self.findFileOrDirectory(path)
        if root == None:
            logging.debug("Failed to select: %s/%s" %(path, name))
            return None, None
        for node in root.iter("*"):
            if self.getNameFromNode(node) == name:
                xmlPath = self.simXml.getPathFromNode(node)
                return node, xmlPath
        return None, None

    def findFileById(self, path, id):
        root, _xmlPath = self.findFileOrDirectory(path)
        if root == None:
            logging.error("Failed to select: %s/%s" %(path, id))
            return None, None
        for node in root.iter("*"):
            try:
                nodeId = node.attrib['id']
            except:
                #not every node has id, e.g. <name>ADF_ISIM</name>
                continue
            if nodeId == id:
                xmlPath = self.simXml.getPathFromNode(node)
                return node, xmlPath
        return None, None

    def findFileOrDirectory(self, path):
        path = self.getFilePath(path)
        if not path:
            return None, None
        xmlPath = self.simXml.getXmlPath(path)
        node = self.simXml.find(xmlPath)
        if node == None:
            if path[-1] != "/":
                #try to select direcotry
                path += "/"
                xmlPath = self.simXml.getXmlPath(path)
                node = self.simXml.find(xmlPath)
            else:
                #try to select file
                path = path.rstrip("/")
                xmlPath = self.simXml.getXmlPath(path)
                node = self.simXml.find(xmlPath)
            if node == None:
                logging.error("Failed to select: %s" %xmlPath)
                return None, None
        return node, xmlPath

    def getNameFromPath(self, path):
        node, xmlPath = self.findFileOrDirectory(path)
        if node == None:
            return None
        return self.simXml.get(node, "name")

    def getNameFromFid(self, fid):
        path = self.findFileByIdInDirs(fid)
        return self.getNameFromPath(path)

    def getNameFromNode(self, node):
        try:
            return self.simXml.get(node, "name")
        except:
            return None

class SimFilesXml(object):
    def __init__(self, simType):
        self.simType = simType
        self.file, self.root = self.readXml(simType)

    def addFileRaw(self, root, name):
        #ef[@id='6F07']"
        node = etree.SubElement(root, "node")
        node.tag = name.split('[')[0]
        node.attrib['id'] = name.split("'")[1]
        return node

    def setNodeAttribute(self, node, attr, value):
        nodeId = node.find(attr)
        if nodeId == None:
            #create attribute
            nodeId = etree.SubElement(node, attr)
        nodeId.text = value

    def fid2Xml(self, simIdXml, fid):
        for path, name in fid.iteritems():
            if name == "MF":
                pass
            xmlPath = self.getXmlPath(path)
            node = self.find(xmlPath)
            if node == None:
                logging.info("adding new path: %s" %xmlPath)
                node = self.addFile(xmlPath)
            #update file attrributes
            self.setNodeAttribute(node, "name", name)

    def joinFile(self, dir, id):
        if not id:
            return dir
        return "%s/ef[@id='%s']" %(dir, id)

    def joinDir(self, dir, id):
        if not id:
            return dir
        path = self.getPathFromXml(dir)
        if not path:
            raise Exception("Couldn't resolve path: %s" %dir)
        fid = types.fidFromPath(path)
        if fid == id:
            return dir
        if id == "3F00":
            return "./mf[@id='3F00']"
        elif id == ".":
            return id
        else:
            return "%s/df[@id='%s']" %(dir, id)

    def getXmlPath(self, path):
        files = path.split("/")
        xmlPath = "."
        for i, _file in enumerate(files):
            if i == 0 and (not _file or _file == '3F00'):
                xmlPath = "./mf[@id='3F00']"
                continue
            elif not _file:
                continue
            if i != len(files) - 1 or _file.startswith("ADF"):
                xmlPath = self.joinDir(xmlPath, _file)
            else:
                xmlPath = self.joinFile(xmlPath, _file)
        return xmlPath

    def writeXml(self, simXmlFile, root):
        xml_document = etree.tostring(root,
                                      pretty_print=True,
                                      xml_declaration=True,
                                      encoding='utf-8')

        file = open(simXmlFile, mode="w")
        file.write(xml_document)
        file.close()

    def readXml(self, simType):
        path = os.path.dirname(__file__)
        if simType == types.TYPE_USIM:
            path = os.path.join(path, "sim_files_3g.xml")
        else:
            path = os.path.join(path, "sim_files_2g.xml")
        tree = etree.ElementTree()
        if not os.path.exists(path):
            logging.warning("File %s not exists" %path)
            logging.info("Create xml")
            if simType == types.TYPE_USIM:
                root = etree.Element('sim_3G')
            else:
                root = etree.Element('sim_2G')
        else:
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.parse(path, parser).getroot()
        return path, root

    def addFile(self, path):
        pathTmp = ""
        previousNode = None
        for _file in path.split("/"):
            if not _file:
                continue
            pathTmp = types.addToPath(pathTmp, _file)
            if _file == ".":
                continue
            node = self.find(pathTmp)
            if node == None:
                if previousNode == None:
                    previousNode = self.root
                node = self.addFileRaw(previousNode, _file)
                node = self.find(pathTmp)
            previousNode = node
        return node

    def find(self, path):
        try:
            node = self.root.find(path)
        except:
           logging.warning("Node: %s not found" %path)
           return None
        return node

    def get(self, node, name):
        subNode = node.find(name)
        if subNode == None:
            raise Exception("%s has no '%s' node" %(node.attrib['id'], name))
        return subNode.text

    def getPathFromXml(self, xmlPath):
        #xmlPath = ./mf[@id='3F00']/df[@id='ADF_ISIM']/ef[@id='6F07']
        if xmlPath.startswith("./mf"):
            xmlPath = xmlPath[2:]
        path = ""
        for _file in xmlPath.split("/"):
            if not _file:
                path += "/"
                continue
            fileIdRe = re.compile(".*id='(.*)'")
            fileIdRaw = fileIdRe.search(_file)
            if not fileIdRaw:
                return None
            fileId = fileIdRaw.group(1)
            path = types.addToPath(path, fileId)
        return path

    def getPathFromNode(self, node):
        pathXml = etree.ElementTree(self.root).getpath(node)
        pathXml = pathXml.split("mf")[1]
        path = "./mf[@id='3F00']"
        for _file in pathXml.split('/'):
            if not _file:
                path = types.addToPath(path, "/")
                continue
            absPath = types.addToPath(path, _file)
            id = etree.ElementTree(self.root).xpath(absPath)[0].attrib['id']
            #"./mf/df[@id='ADF0']"
            fileId = "%s[@id='%s']" %(_file.split('[')[0], id)
            path = types.addToPath(path, fileId)
        return path

def fids2Xml():
    gsmFiles = SIM_DF_FID
    umtsDfFiles = USIM_DF_FID
    umtsAdfFiles = USIM_ADF_FID
    isimAdfFiles = ISIM_ADF_FID
    otherDfFiles = OTHER_DF_FID

    simIdXml = SimFilesXml(types.TYPE_SIM)
    simIdXml.fid2Xml(simIdXml, gsmFiles)
    simIdXml.writeXml(simIdXml.file, simIdXml.root)

    simIdXml = SimFilesXml(types.TYPE_USIM)
    simIdXml.fid2Xml(simIdXml, gsmFiles)
    simIdXml.fid2Xml(simIdXml, umtsDfFiles)
    simIdXml.fid2Xml(simIdXml, umtsAdfFiles)
    simIdXml.fid2Xml(simIdXml, isimAdfFiles)
    simIdXml.fid2Xml(simIdXml, otherDfFiles)
    simIdXml.writeXml(simIdXml.file, simIdXml.root)

#Change to update xml with new EF, DF
SIM_DF_FID = {
    '/3F00/' : 'MF',
    '/2F05' : 'EF_ELP',
    '/2FE2' : 'EF_ICCID',

    '/7F20/' : 'DF_GSM',
    '/7F20/5F3C/' : 'DF_MEXE',
    '/7F20/5F30/' : 'DF_IRIDIUM',
    '/7F20/5F31/' : 'DF_GLOBALSTAR',
    '/7F20/5F32/' : 'DF_ICO',
    '/7F20/5F33/' : 'DF_ACES',
    '/7F20/5F40/' : 'DF_PCS_1900',
    '/7F20/5F60/' : 'DF_CTS',
    '/7F20/5F70/' : 'DF_SOLSA',

    '/7F10/' : 'DF_TELECOM',
    '/7F10/5F50/' : 'DF_GRAPHICS',

    '/7F22/' : 'DF_IS_41',
    '/7F23/' : 'DF_FP_CTS',

    '/7F10/6F06' : 'EF_ARR',
    '/7F10/6F3A' : 'EF_ADN',
    '/7F10/6F3B' : 'EF_FDN',
    '/7F10/6F3C' : 'EF_SMS',
    '/7F10/6F3D' : 'EF_CCP',
    '/7F10/6F40' : 'EF_MSISDN',
    '/7F10/6F42' : 'EF_SMSP',
    '/7F10/6F43' : 'EF_SMSS',
    '/7F10/6F44' : 'EF_LND',
    '/7F10/6F47' : 'EF_SMSR',
    '/7F10/6F49' : 'EF_SDN',
    '/7F10/6F4A' : 'EF_EXT1',
    '/7F10/6F4B' : 'EF_EXT2',
    '/7F10/6F4C' : 'EF_EXT3',
    '/7F10/6F4D' : 'EF_BDN',
    '/7F10/6F4E' : 'EF_EXT4',
    '/7F10/6F4F' : 'EF_ECCP',
    '/7F10/6F58' : 'EF_CMI',
    '/7F10/5F50/6F06' : 'EF_ARR',
    '/7F10/5F50/4F20' : 'EF_IMG',

    '/7F10/5F3C/6F06' : 'EF_ARR',
    '/7F20/5F3C/4F40' : 'EF_MEXE-ST',
    '/7F20/5F3C/4F41' : 'EF_ORPK',
    '/7F20/5F3C/4F42' : 'EF_ARPK',
    '/7F20/5F3C/4F43' : 'EF_TPRK',
    '/7F20/5F70/4F30' : 'EF_SAI',
    '/7F20/5F70/4F31' : 'EF_SLL',

    '/7F20/6F05' : 'EF_LP',
    '/7F20/6F06' : 'EF_ARR',
    '/7F20/6F07' : 'EF_IMSI',
    '/7F20/6F11' : 'EF_CPHS_VMW',
    '/7F20/6F12' : 'EF_CPHS_SST',
    '/7F20/6F13' : 'EF_CPHS_CFF',
    '/7F20/6F14' : 'EF_CPHS_ONSTR',
    '/7F20/6F15' : 'EF_CPHS_CSP',
    '/7F20/6F16' : 'EF_CPHS',
    '/7F20/6F17' : 'EF_CPHS_MBXN',
    '/7F20/6F18' : 'EF_CPHS_ONSHF',
    '/7F20/6F19' : 'EF_CPHS_INFN',
    '/7F20/6F20' : 'EF_KC',
    '/7F20/6F2C' : 'EF_DCK',
    '/7F20/6F30' : 'EF_PLMNSEL',
    '/7F20/6F31' : 'EF_HPLMN',
    '/7F20/6F32' : 'EF_CNL',
    '/7F20/6F37' : 'EF_ACMMAX',
    '/7F20/6F38' : 'EF_SST',
    '/7F20/6F39' : 'EF_ACM',
    '/7F20/6F3E' : 'EF_GID1',
    '/7F20/6F3F' : 'EF_GID2',
    '/7F20/6F41' : 'EF_PUCT',
    '/7F20/6F45' : 'EF_CBMI',
    '/7F20/6F46' : 'EF_SPN',
    '/7F20/6F47' : 'EF_SMSR',
    '/7F20/6F48' : 'EF_CBMID',
    '/7F20/6F74' : 'EF_BCCH',
    '/7F20/6F78' : 'EF_ACC',
    '/7F20/6F7B' : 'EF_FPLMN',
    '/7F20/6F7E' : 'EF_LOCI',
    '/7F20/6FAD' : 'EF_AD',
    '/7F20/6FAE' : 'EF_PHASE',
    '/7F20/6FB1' : 'EF_VGCS',
    '/7F20/6FB2' : 'EF_VGCSS',
    '/7F20/6FB3' : 'EF_VBS',
    '/7F20/6FB4' : 'EF_VBSS',
    '/7F20/6FB5' : 'EF_EMLPP',
    '/7F20/6FB6' : 'EF_AAEM',
    '/7F20/6FB7' : 'EF_ECC',
    '/7F20/6F50' : 'EF_CBMIR',
    '/7F20/6F51' : 'EF_NIA',
    '/7F20/6F52' : 'EF_KCGPRS',
    '/7F20/6F53' : 'EF_LOCIGPRS',
    '/7F20/6F54' : 'EF_SUME',
    '/7F20/6F60' : 'EF_PLMNWACT',
    '/7F20/6F61' : 'EF_OPLMNWACT',
    '/7F20/6F62' : 'EF_HPLMNWACT',
    '/7F20/6F63' : 'EF_CPBCCH',
    '/7F20/6F64' : 'EF_INVSCAN',
    '/7F20/6F65' : 'EF_RPLMN_ACT',
    '/7F20/6FC5' : 'EF_PNN',
    '/7F20/6FC6' : 'EF_OPL',
    '/7F20/6FC7' : 'EF_MBDN',
    '/7F20/6FC8' : 'EF_EXT6',
    '/7F20/6FC9' : 'EF_MBI',
    '/7F20/6FCA' : 'EF_MWIS',
    '/7F20/6FCB' : 'EF_CFIS',
    '/7F20/6FCC' : 'EF_EXT7',
    '/7F20/6FCD' : 'EF_SPDI',
    '/7F20/6FCE' : 'EF_MMSN',
    '/7F20/6FCF' : 'EF_EXT8',
    '/7F20/6FD0' : 'EF_MMSICP',
    '/7F20/6FD1' : 'EF_MMSUP',
    '/7F20/6FD2' : 'EF_MMSUCP',
    }

OTHER_DF_FID = {
    '/7F21/' : 'DF_DCS_1800',
    '/7F24/' : 'DF_TIA_EIA_136',
    '/7F25/' : 'DF_TIA_EIA_95',
    '/7F66/' : 'DF_CING',
    '/7F80/' : 'DF_PDC',
    '/7F90/' : 'DF_TETRA',
    }

USIM_DF_FID = {
    '/7F10/5F3A/' : 'DF_PHONEBOOK',
    '/7F10/5F3B/' : 'DF_MULTIMEDIA',
    '/7F10/5F3C/' : 'DF_MMSS',
    '/7F11/' : 'DF_CD',
    '/7F40/' : 'DF_ORANGE',

    '/2F00' : 'EF_DIR',
    '/2F05' : 'EF_PL',
    '/2F06' : 'EF_ARR',
    '/2F08' : 'EF_UMPC',

    '/7F10/6F53' : 'EF_RMA',
    '/7F10/6F54' : 'EF_SUME',
    '/7F10/6FE0' : 'EF_ICE_DN',
    '/7F10/6FE1' : 'EF_ICE_FF',
    '/7F10/6FE5' : 'EF_PSISMSC',
    #'/7F10/5F50/4FXX' : 'EF_IIDFn',
    '/7F10/5F50/4F21' : 'EF_ICE_graphics',
    '/7F10/5F50/4F01' : 'EF_LAUNCH_SCWS',
    #'/7F10/5F50/4FXX' : 'EF_ICON',

    '/7F10/5F3A/4F09' : 'EF_PBC',
    '/7F10/5F3A/4F11' : 'EF_ANRA',
    '/7F10/5F3A/4F12' : 'EF_ANRB',
    '/7F10/5F3A/4F15' : 'EF_ANRC',
    '/7F10/5F3A/4F19' : 'EF_SNE',
    '/7F10/5F3A/4F21' : 'EF_UID',
    '/7F10/5F3A/4F22' : 'EF_PSC',
    '/7F10/5F3A/4F23' : 'EF_CC',
    '/7F10/5F3A/4F24' : 'EF_PUID',
    '/7F10/5F3A/4F26' : 'EF_GRP',
    '/7F10/5F3A/4F30' : 'EF_PBR',
    '/7F10/5F3A/4F3A' : 'EF_ADN',
    '/7F10/5F3A/4F4A' : 'EF_EXT1',
    '/7F10/5F3A/4F4B' : 'EF_AAS',
    '/7F10/5F3A/4F4C' : 'EF_GAS',
    '/7F10/5F3A/4F50' : 'EF_EMAIL',
    '/7F10/5F3A/4F54' : 'EF_PURI',
    '/7F10/5F3A/6F06' : 'EF_ARR',

    '/7F10/5F3B/6F06' : 'EF_ARR',
    '/7F10/5F3B/4F47' : 'EF_MML',
    '/7F10/5F3B/4F48' : 'EF_MMDF',
}

USIM_ADF_FID = {
    '/ADF_USIM/'      : 'ADF_USIM',
    '/ADF_USIM/5F3A/' : 'DF_PHONEBOOK',
    '/ADF_USIM/5F3B/' : 'DF_GSM_ACCESS',
    '/ADF_USIM/5F3C/' : 'DF_MEXE',
    '/ADF_USIM/5F70/' : 'DF_SOLSA',
    '/ADF_USIM/5F40/' : 'DF_WLAN',
    '/ADF_USIM/5F50/' : 'DF_HNB',
    '/ADF_USIM/5F80/' : 'DF_BCAST',
    '/ADF_USIM/5F90/' : 'DF_PROSE',
    '/ADF_USIM/6F05' : 'EF_LI',
    '/ADF_USIM/6F06' : 'EF_ARR',
    '/ADF_USIM/6F07' : 'EF_IMSI',
    '/ADF_USIM/6F08' : 'EF_KEYS',
    '/ADF_USIM/6F09' : 'EF_KEYSPS',
    '/ADF_USIM/6F11' : 'EF_CPHS_VMW',
    '/ADF_USIM/6F12' : 'EF_CPHS_SST',
    '/ADF_USIM/6F13' : 'EF_CPHS_CFF',
    '/ADF_USIM/6F14' : 'EF_CPHS_ONSTR',
    '/ADF_USIM/6F15' : 'EF_CPHS_CSP',
    '/ADF_USIM/6F16' : 'EF_CPHS',
    '/ADF_USIM/6F17' : 'EF_CPHS_MBXN',
    '/ADF_USIM/6F18' : 'EF_CPHS_ONSHF',
    '/ADF_USIM/6F19' : 'EF_CPHS_INFN',
    '/ADF_USIM/6F2C' : 'EF_DCK',
    '/ADF_USIM/6F31' : 'EF_HPPLMN',
    '/ADF_USIM/6F32' : 'EF_CNL',
    '/ADF_USIM/6F37' : 'EF_ACMmax',
    '/ADF_USIM/6F38' : 'EF_UST',
    '/ADF_USIM/6F39' : 'EF_ACM',
    '/ADF_USIM/6F3B' : 'EF_FDN',
    '/ADF_USIM/6F3C' : 'EF_SMS',
    '/ADF_USIM/6F3E' : 'EF_GID1',
    '/ADF_USIM/6F3F' : 'EF_GID2',
    '/ADF_USIM/6F40' : 'EF_MSISDN',
    '/ADF_USIM/6F41' : 'EF_PUCT',
    '/ADF_USIM/6F42' : 'EF_SMSP',
    '/ADF_USIM/6F43' : 'EF_SMSS',
    '/ADF_USIM/6F45' : 'EF_CBMI',
    '/ADF_USIM/6F46' : 'EF_SPN',
    '/ADF_USIM/6F47' : 'EF_SMSR',
    '/ADF_USIM/6F48' : 'EF_CBMID',
    '/ADF_USIM/6F49' : 'EF_SDN',
    '/ADF_USIM/6F4B' : 'EF_EXT2',
    '/ADF_USIM/6F4C' : 'EF_EXT3',
    '/ADF_USIM/6F4D' : 'EF_BDN',
    '/ADF_USIM/6F4E' : 'EF_EXT5',
    '/ADF_USIM/6F4F' : 'EF_CCP2',
    '/ADF_USIM/6F50' : 'EF_CBMIR',
    '/ADF_USIM/6F55' : 'EF_EXT4',
    '/ADF_USIM/6F56' : 'EF_EST',
    '/ADF_USIM/6F57' : 'EF_ACL',
    '/ADF_USIM/6F58' : 'EF_CMI',
    '/ADF_USIM/6F5B' : 'EF_START-HFN',
    '/ADF_USIM/6F5C' : 'EF_THRESHOLD',
    '/ADF_USIM/6F60' : 'EF_PLMNwAcT',
    '/ADF_USIM/6F61' : 'EF_OPLMNwAcT',
    '/ADF_USIM/6F62' : 'EF_HPLMNwAcT',
    '/ADF_USIM/6F73' : 'EF_PSLOCI',
    '/ADF_USIM/6F78' : 'EF_ACC',
    '/ADF_USIM/6F7B' : 'EF_FPLMN',
    '/ADF_USIM/6F7E' : 'EF_LOCI',
    '/ADF_USIM/6F80' : 'EF_ICI',
    '/ADF_USIM/6F81' : 'EF_OCI',
    '/ADF_USIM/6F82' : 'EF_ICT',
    '/ADF_USIM/6F83' : 'EF_OCT',
    '/ADF_USIM/6FAD' : 'EF_AD',
    '/ADF_USIM/6FB1' : 'EF_VGCS',
    '/ADF_USIM/6FB2' : 'EF_VGCSS',
    '/ADF_USIM/6FB3' : 'EF_VBS',
    '/ADF_USIM/6FB4' : 'EF_VBSS',
    '/ADF_USIM/6FB5' : 'EF_EMLPP',
    '/ADF_USIM/6FB6' : 'EF_AAEM',
    '/ADF_USIM/6FB7' : 'EF_ECC',
    '/ADF_USIM/6FC3' : 'EF_HIDDENKEY',
    '/ADF_USIM/6FC4' : 'EF_NETPAR',
    '/ADF_USIM/6FC5' : 'EF_PNN',
    '/ADF_USIM/6FC6' : 'EF_OPL',
    '/ADF_USIM/6FC7' : 'EF_MBDN',
    '/ADF_USIM/6FC8' : 'EF_EXT6',
    '/ADF_USIM/6FC9' : 'EF_MBI',
    '/ADF_USIM/6FCA' : 'EF_MWIS',
    '/ADF_USIM/6FCB' : 'EF_CFIS',
    '/ADF_USIM/6FCC' : 'EF_EXT7',
    '/ADF_USIM/6FCD' : 'EF_SPDI',
    '/ADF_USIM/6FCE' : 'EF_MMSN',
    '/ADF_USIM/6FCF' : 'EF_EXT8',
    '/ADF_USIM/6FD0' : 'EF_MMSICP',
    '/ADF_USIM/6FD1' : 'EF_MMSUP',
    '/ADF_USIM/6FD2' : 'EF_MMSUCP',
    '/ADF_USIM/6FD3' : 'EF_NIA',
    '/ADF_USIM/6FD4' : 'EF_VGCSCA',
    '/ADF_USIM/6FD5' : 'EF_VBSCA',
    '/ADF_USIM/6FD6' : 'EF_GBABP',
    '/ADF_USIM/6FD7' : 'EF_MSK',
    '/ADF_USIM/6FD8' : 'EF_MUK',
    '/ADF_USIM/6FD9' : 'EF_EHPLMN',
    '/ADF_USIM/6FDA' : 'EF_GBANL',
    '/ADF_USIM/6FDB' : 'EF_EHPLMNPI',
    '/ADF_USIM/6FDC' : 'EF_LRPLMNSI',
    '/ADF_USIM/6FDD' : 'EF_NAFKCA',
    '/ADF_USIM/6FDE' : 'EF_SPNI',
    '/ADF_USIM/6FDF' : 'EF_PNNI',
    '/ADF_USIM/6FE2' : 'EF_NCP-IP',
    '/ADF_USIM/6FE3' : 'EF_EPSLOCI',
    '/ADF_USIM/6FE4' : 'EF_EPSNSC',
    '/ADF_USIM/6FE6' : 'EF_UFC',
    '/ADF_USIM/6FE7' : 'EF_UICCIARI',
    '/ADF_USIM/6FE8' : 'EF_NASCONFIG',
    '/ADF_USIM/6FEC' : 'EF_PWS',
    '/ADF_USIM/6FED' : 'EF_FDNURI',
    '/ADF_USIM/6FEE' : 'EF_BDNURI',
    '/ADF_USIM/6FEF' : 'EF_SDNURI',
    '/ADF_USIM/6FF0' : 'EF_IWL',
    '/ADF_USIM/6FF1' : 'EF_IPS',
    '/ADF_USIM/6FF2' : 'EF_IPD',
    '/ADF_USIM/6FF3' : 'EF_EPDGID',
    '/ADF_USIM/6FF4' : 'EF_EPDSELECTION',
    '/ADF_USIM/5F3A/4F09' : 'EF_PBC',
    '/ADF_USIM/5F3A/4F0A' : 'EF_PBC1',
    '/ADF_USIM/5F3A/4F11' : 'EF_ANRA',
    '/ADF_USIM/5F3A/4F12' : 'EF_ANRA1',
    '/ADF_USIM/5F3A/4F13' : 'EF_ANRB',
    '/ADF_USIM/5F3A/4F14' : 'EF_ANRB1',
    '/ADF_USIM/5F3A/4F15' : 'EF_ANRC',
    '/ADF_USIM/5F3A/4F16' : 'EF_ANRC1',
    '/ADF_USIM/5F3A/4F19' : 'EF_SNE',
    '/ADF_USIM/5F3A/4F1A' : 'EF_SNE1',
    '/ADF_USIM/5F3A/4F21' : 'EF_UID',
    '/ADF_USIM/5F3A/4F22' : 'EF_PSC',
    '/ADF_USIM/5F3A/4F23' : 'EF_CC',
    '/ADF_USIM/5F3A/4F24' : 'EF_PUID',
    '/ADF_USIM/5F3A/4F25' : 'EF_GRP1',
    '/ADF_USIM/5F3A/4F26' : 'EF_GRP',
    '/ADF_USIM/5F3A/4F30' : 'EF_PBR',
    '/ADF_USIM/5F3A/4F3A' : 'EF_ADN',
    '/ADF_USIM/5F3A/4F3B' : 'EF_ADN1',
    '/ADF_USIM/5F3A/4F4A' : 'EF_EXT1',
    '/ADF_USIM/5F3A/4F4B' : 'EF_AAS',
    '/ADF_USIM/5F3A/4F4C' : 'EF_GAS',
    '/ADF_USIM/5F3A/4F50' : 'EF_EMAIL',
    '/ADF_USIM/5F3A/4F54' : 'EF_PURI',
    '/ADF_USIM/5F3A/4F55' : 'EF_PURI1',
    '/ADF_USIM/5F3A/6F06' : 'EF_ARR',

    '/ADF_USIM/5F3B/4F20' : 'EF_KC',
    '/ADF_USIM/5F3B/4F52' : 'EF_KCGPRS',
    '/ADF_USIM/5F3B/4F63' : 'EF_CPBCCH',
    '/ADF_USIM/5F3B/4F64' : 'EF_INVSCAN',
    '/ADF_USIM/5F3B/6F06' : 'EF_ARR',
    '/ADF_USIM/5F3C/4F40' : 'EF_MEXE-ST',
    '/ADF_USIM/5F3C/4F41' : 'EF_ORPK',
    '/ADF_USIM/5F3C/4F42' : 'EF_ARPK',
    '/ADF_USIM/5F3C/4F43' : 'EF_TPRK',
    '/ADF_USIM/5F3C/6F06' : 'EF_ARR',
    #'/ADF_USIM/5F3C/4FXX' : 'EF_TKCDF',
    '/ADF_USIM/5F70/4F30' : 'EF_SAI',
    '/ADF_USIM/5F70/4F31' : 'EF_SLL',
    '/ADF_USIM/5F70/6F06' : 'EF_ARR',
    '/ADF_USIM/5F40/4F41' : 'EF_PSEUDO',
    '/ADF_USIM/5F40/4F42' : 'EF_UPLMNWLAN',
    '/ADF_USIM/5F40/4F43' : 'EF_0PLMNWLAN',
    '/ADF_USIM/5F40/4F44' : 'EF_UWSIDL',
    '/ADF_USIM/5F40/4F45' : 'EF_OWSIDL',
    '/ADF_USIM/5F40/4F46' : 'EF_WRI',
    '/ADF_USIM/5F40/4F47' : 'EF_HWSIDL',
    '/ADF_USIM/5F40/4F48' : 'EF_WEHPLMNPI',
    '/ADF_USIM/5F40/4F49' : 'EF_WHPI',
    '/ADF_USIM/5F40/4F4A' : 'EF_WLRPLMN',
    '/ADF_USIM/5F40/4F4B' : 'EF_HPLMNDAI',
    '/ADF_USIM/5F40/6F06' : 'EF_ARR',
    '/ADF_USIM/5F50/4F81' : 'EF_ACSGL',
    '/ADF_USIM/5F50/4F82' : 'EF_CSGT',
    '/ADF_USIM/5F50/4F83' : 'EF_HNBN',
    '/ADF_USIM/5F50/4F84' : 'EF_OCSGL',
    '/ADF_USIM/5F50/4F85' : 'EF_OCSGT',
    '/ADF_USIM/5F50/4F86' : 'EF_OHNBN',
    '/ADF_USIM/5F50/6F06' : 'EF_ARR',
    '/ADF_USIM/5F90/4F01' : 'EF_PROSE_MON',
    '/ADF_USIM/5F90/4F02' : 'EF_PROSE_ANN',
    '/ADF_USIM/5F90/4F03' : 'EF_PROSEFUNC',
    '/ADF_USIM/5F90/4F04' : 'EF_PROSE_RADIO_COM',
    '/ADF_USIM/5F90/4F05' : 'EF_PROSE_RADIO_MON',
    '/ADF_USIM/5F90/4F06' : 'EF_PROSE_RADIO_ANN',
    '/ADF_USIM/5F90/4F07' : 'EF_PROSE_POLICY',
    '/ADF_USIM/5F90/4F08' : 'EF_PROSE_PLMN',
    '/ADF_USIM/5F90/4F09' : 'EF_PROSE_GC',
    '/ADF_USIM/5F90/6F06' : 'EF_ARR',
}

ISIM_ADF_FID = {
    '/ADF_ISIM/'     : 'ADF_ISIM',
    '/ADF_ISIM/6F02' : 'EF_IMPI',
    '/ADF_ISIM/6F03' : 'EF_DOMAIN',
    '/ADF_ISIM/6F04' : 'EF_IMPU',
    '/ADF_ISIM/6F06' : 'EF_ARR',
    '/ADF_ISIM/6F07' : 'EF_IST',
    '/ADF_ISIM/6F09' : 'EF_P-CSCF',
    '/ADF_ISIM/6F3C' : 'EF_SMS',
    '/ADF_ISIM/6F42' : 'EF_SMSP',
    '/ADF_ISIM/6F43' : 'EF_SMSS',
    '/ADF_ISIM/6F47' : 'EF_SMSR',
    '/ADF_ISIM/6FAD' : 'EF_AD',
    '/ADF_ISIM/6FD5' : 'EF_GBABP',
    '/ADF_ISIM/6FD7' : 'EF_GBANL',
    '/ADF_ISIM/6FDD' : 'EF_NAFKCA',
    '/ADF_ISIM/6FE7' : 'EF_UICCIARI',
}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    fids2Xml()
