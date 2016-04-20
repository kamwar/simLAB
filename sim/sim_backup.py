#!/usr/bin/python
# LICENSE: GPL2
# (c) 2016 Kamil Wartanowicz

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from util import types
from sim_soft import sim_xml

class SimBackup(object):
    def __init__(self, simCtrl, imsi, atr):
        self.simCtrl = simCtrl
        self.imsi = imsi
        self.root = sim_xml.xmlInit(atr)

    def setMf(self, data):
        return self.addMf(self.root, data)

    def addMf(self, node, data):
        arrFile, arrRecord = types.getArrFileFromData(data)
        if not arrFile:
            #TODO: handle security attr
            arrFile = "2F06"
            arrRecord = "2"
        return sim_xml.addMfNode(node, str(arrFile), str(arrRecord))

    def addDf(self, node, id, data):
        arrFile, arrRecord = types.getArrFileFromData(data)
        if not arrFile:
            #TODO: handle security attr
            arrFile = "2F06"
            arrRecord = "2"
        return sim_xml.addDfNode(node, id, str(arrFile), str(arrRecord))

    def addAdf(self, node, id, aid, data):
        arrFile, arrRecord = types.getArrFileFromData(data)
        if not arrFile:
            #TODO: handle security attr
            arrFile = "2F06"
            arrRecord = "2"
        return sim_xml.addAdfNode(node, id, aid, str(arrFile), str(arrRecord))

    def addEf(self, node, id, value, data):
        struct = self.simCtrl.getFileStructure(data)
        if self.simCtrl.getFileStructure(data) in [types.FILE_STRUCTURE_LINEAR_FIXED,
                                                   types.FILE_STRUCTURE_CYCLIC]:
            recordLength, nbrOfRecords = self.simCtrl.getRecordInfo(data)
            size = recordLength * nbrOfRecords
        else:
            recordLength = 0
            size = types.getFileLength(data)
        #TODO: for older 3G cards security attr might be used instead of arr
        arrFile, arrRecord = types.getArrFileFromData(data)
        if not arrFile:
            #TODO: handle security attr
            arrFile = "6F06"
            arrRecord = "2"
        sfi = "%02X" %types.getSfiFromData(data)
        #TODO: get from data
        invalidated = 0
        rwInvalidated = 0
        sim_xml.addEfNode(node,
                          id,
                          sfi,
                          str(struct),
                          str(size),
                          str(recordLength),
                          value,
                          arrFile,
                          str(arrRecord),
                          str(invalidated),
                          str(rwInvalidated))

    def saveXml(self):
        xmlPath = os.path.dirname(__file__) + "/../sim_soft/sim_backup_" + self.imsi + ".xml"
        sim_xml.writeXml(xmlPath, self.root)
        return xmlPath