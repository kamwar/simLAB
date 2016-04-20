#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015, Kamil Wartanowicz <k.wartanowicz@gmail.com>
from util import hextools
from util import types
from util import coder

MODE_GET = 0
MODE_SET = 1

class FileParser(object):
    def __init__(self):
        pass

    def getEfImsi(self, data):
        data = hextools.hex2bytes(data)
        imsi = hextools.decode_BCD(data)[3:]
        return imsi

    def setEfImsi(self, imsi):
        if len(imsi) % 2:
            dataLow = 9
        else:
            dataLow = 1
        firstByte = dataLow<<4 | int(imsi[0], 16)
        imsi = "%02X%s" %(firstByte, imsi[1:])
        imsi = hextools.encode_BCD(imsi)
        return "08%s" %hextools.bytes2hex(imsi)

    def getEfUst(self, data):
        data = hextools.hex2bytes(data)
        ustTable = []
        for byte in data:
            for bitId in range(8):
                value = int(byte & (1 << bitId) != 0)
                ustTable.append(value)
        return ustTable

    def setEfUst(self, data):
        ustTable = data
        ustRaw = []
        for i, bitValue in enumerate(ustTable):
            byteId = i / 8
            bitId = i % 8
            if len(ustRaw) <= byteId:
                ustRaw.append(0x00)
            if bitValue:
                ustRaw[byteId] |= (1 << bitId)
            else:
                ustRaw[byteId] &= ~(1 << bitId)
        return hextools.bytes2hex(ustRaw)

    def getEfEcc(self, data):
        eccStr = ''
        data = data.split(';')
        for record in data:
            recordRaw = hextools.hex2bytes(record)
            number = hextools.decode_BCD(recordRaw[0:3])
            number = number.replace('F','')
            if not number:
                continue
            #number = type.removeTrailingBytes(hextools.hex2bytes(number), 0xFF)
            aplha = None
            category = recordRaw[-1]
            eccStr += "number=%s,alpha=%s,cat=%d;" %(number, aplha, category)
        eccStr = eccStr.rstrip(";")
        if not eccStr:
            eccStr = "EMPTY"
        return eccStr

    def setEfEcc(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            number = types.getParamValue(record, "number")
            if not number:
                return False
            category = types.getParamValue(record, "cat")
            number = number.replace('F','')
            if number:
                numberBcd = hextools.encode_BCD(number)
                numberBcd = hextools.bytes2hex(numberBcd)
                numberBcd = types.addTrailingBytes(numberBcd, 0xFF, 3)
            else:
                numberBcd = "FFFFFF"
            dataTmp = numberBcd
            if category:
                raise Exception("Not implemented")
                #TODO: move it to the last byte
                dataTmp += "%02X" %int(category)
            if dataNew:
                dataNew = "%s;%s" %(dataNew, dataTmp)
            else:
                dataNew = dataTmp
        return dataNew

    def getEfSpn(self, data):
        spnRaw = types.removeTrailingBytes(hextools.hex2bytes(data), 0xFF)
        if spnRaw:
            displayByte = spnRaw[0]
            name = hextools.bytes2hex(spnRaw[1:]).decode("hex")
        else:
            return ''
        return "name=%s,display=%02X" %(name, displayByte)

    def setEfSpn(self, value):
        name = types.getParamValue(value, "name")
        if not name:
            raise Exception("Name not provided")
        displayByte = types.getParamValue(value, "display")
        if displayByte:
            displayByte = int(displayByte)
        else:
            #display is not provided, set default value
            displayByte = 0x00
        value = "%02X%s" %(displayByte, name.encode('hex'))
        return value

    def getEfCphs_onstr(self, data):
        nameHex = types.removeTrailingBytes(hextools.hex2bytes(data), 0xFF)
        #fullName = coder.decodeGsm7(hextools.bytes2hex(nameHex))
        #return fullName
        return hextools.bytes2hex(nameHex.decode("hex"))

    def setEfCphs_onstr(self, name):
        #return coder.encodeGsm7(data)
        return  name.encode('hex')

    def getEfImpu(self, data):
        impuStr = ''
        data = data.split(';')
        for record in data:
            value = types.removeTrailingBytes(hextools.hex2bytes(record), 0xFF)
            if len(value) < 3:
                continue
            if impuStr:
                impuStr += ";"
            impuStr += hextools.bytes2hex(value[2:]).decode("hex")
        return impuStr

    def setEfImpu(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            tag = 0x80
            length = len(record)
            value = "%02X%02X%s" %(tag, length, record.encode('hex'))
            if dataNew:
                dataNew += ";"
            dataNew += value
        return dataNew

    def getEfImpi(self, data):
        valueRaw = types.removeTrailingBytes(hextools.hex2bytes(data), 0xFF)
        if len(valueRaw) < 3:
            return ''
        value = hextools.bytes2hex(valueRaw[2:]).decode("hex")
        return "impi=%s" %value

    def setEfImpi(self, data):
        impi = types.getParamValue(data, "impi")
        if not impi:
            raise Exception("impi not provided")
        tag = 0x80
        length = len(impi)
        value = "%02X%02X%s" %(tag, length, impi.encode('hex'))
        return value

    def getEfPcscf(self, data):
        #TODO: handle many records
        firstRecord = data.split(';')[0]
        value = types.removeTrailingBytes(hextools.hex2bytes(firstRecord), 0xFF)
        if len(value) < 3:
            return ''
        cscf = hextools.bytes2hex(value[3:]).decode("hex")
        return "cscf=%s" %cscf

    def setEfPcscf(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            cscf = types.getParamValue(record, "cscf")
            if not cscf:
                raise Exception("cscf not provided")
            tag = 0x80
            length = len(cscf) + 1
            '''
            Value | Name
            ============
            '00'  | FQDN
            '01'  | IPv4
            '02'  | IPv6
            '''
            addrType = 0x00
            value = "%02X%02X%02X%s" %(tag, length, addrType, cscf.encode('hex'))
            if dataNew:
                dataNew += ";"
            dataNew += value
        return dataNew

    def getEfLoci(self, data):
        valueRaw = hextools.hex2bytes(data)
        tmsi = hextools.bytes2hex(valueRaw[0:4])
        lai = hextools.bytes2hex(valueRaw[4:9])
        #TODO: check for mnc containing 3digits
        mcc_mnc = hextools.decode_BCD(hextools.hex2bytes(lai)[0:3])
        lac = lai[6:10]
        rfu = hextools.bytes2hex([valueRaw[9]])
        loction_status = hextools.bytes2hex([valueRaw[10]])
        '''
        loction_status
        Bits: b3 b2 b1
              0 0 0 : updated.
              0 0 1 : not updated.
              0 1 0 : PLMN not allowed.
              0 1 1 : Location Area not allowed.
              1 1 1 : reserved
        '''
        return "tmsi=%s,mcc_mnc=%s,lac=%s,loc_status=%s"\
                %(tmsi, mcc_mnc, lac, loction_status)

    def setEfLoci(self, data):
        param = "tmsi"
        tmsi = types.getParamValue(data, param)
        if not tmsi:
            raise Exception("%s not provided" %param)

        param = "lai"
        lai = types.getParamValue(data, param)
        if not lai:
            #if lai is not provided, check mcc_mnc and lac
            param = "mcc_mnc"
            mccMnc = types.getParamValue(data, param)
            if not mccMnc:
                raise Exception("%s not provided" %param)
            if len(mccMnc) != 6:
                mnc3 = 'F'
            else:
                mnc3 = mccMnc[5]
            mccMnc = "%s%s%s" %(mccMnc[0:3], mnc3, mccMnc[3:5])

            param = "lac"
            lac = types.getParamValue(data, param)
            if not lac:
                raise Exception("%s not provided" %param)
            lai = "%s%04X" %(hextools.bytes2hex(hextools.encode_BCD(mccMnc)), int(lac, 16))
        param = "rfu"
        rfu = types.getParamValue(data, param)
        if not rfu:
            rfu = "FF"

        param = "loc_status"
        locStatus = types.getParamValue(data, param)
        if not locStatus:
            locStatus = "00"

        loci = "%s%s%s%s" %(tmsi, lai, rfu, locStatus)
        return loci

    def getEfPnn(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            if not record:
                continue
            binRecord = hextools.hex2bytes(record)
            if binRecord.count(0xFF) == len(binRecord):
                continue
            fullNameRaw = types.parseTlv(binRecord, types.FULL_NW_NAME_TAG)
            shortNameRaw = types.parseTlv(binRecord, types.SHORT_NW_NAME_TAG)
            additionalInfo = types.parseTlv(binRecord, types.ADDITIONAL_INFORMATION_PLMN_TAG)
            if fullNameRaw:
                infoByte = fullNameRaw[0]
                spareBits = infoByte & 0b00000111
                ci = infoByte >> 3 & 0b00000001
                dcs = infoByte >> 4 & 0b00000111
                if dcs != 0x00:
                    raise Exception("Only GSM coding is supported in DCS, current coding: %02X" %dcs)
                fullName = coder.decodeGsm7(hextools.bytes2hex(fullNameRaw[1:]))
            else:
                fullName = None
            if shortNameRaw:
                infoByte = shortNameRaw[0]
                spareBits = infoByte & 0b00000111
                ci = infoByte >> 3 & 0b00000001
                dcs = infoByte >> 4 & 0b00000111
                if dcs != 0x00:
                    raise Exception("Only GSM coding is supported in DCS, current coding: %02X" %dcs)
                shortName = coder.decodeGsm7(hextools.bytes2hex(shortNameRaw[1:]))
            else:
                shortName = None
            dataNew += "full_name=%s,short_name=%s"\
                    %(fullName, shortName)
            if additionalInfo:
                dataNew += ",additional_info=%s" %additionalInfo
            dataNew += ";"
        return dataNew

    def setEfPnn(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            if not record:
                continue
            tmpData = []
            infoFull = types.getParamValue(record, "info_full")
            fullName = types.getParamValue(record, "full_name")
            infoShort = types.getParamValue(record, "info_short")
            shortName = types.getParamValue(record, "short_name")
            additionalInfo = types.getParamValue(record, "additional_info")
            if fullName:
                fullNameGsm7 = coder.encodeGsm7(fullName)
                if infoFull:
                    infoByte = int(infoFull, 16)
                    spareBits = infoByte & 0b00000111
                    ci = infoByte >> 3 & 0b00000001
                    dcs = infoByte >> 4 & 0b00000111
                    if dcs != 0x00:
                        raise Exception("Only GSM coding is supported in DCS")
                    ext = infoByte >> 7 & 0b00000001
                else:
                    spareBits = len(fullName) % 8
                    ci = 0 #don't add the letters for the Country's Initials
                    dcs = 0 #GSM
                    ext = 1 #?
                    infoByte = ext << 7 | dcs << 3 | ci << 2 | spareBits
                fullNameGsm7 = "%02X%s" %(infoByte, fullNameGsm7)
                types.addTlv(tmpData, types.FULL_NW_NAME_TAG, hextools.hex2bytes(fullNameGsm7))
            if shortName:
                shortNameGsm7 = coder.encodeGsm7(shortName)
                if infoShort:
                    infoByte = int(infoShort, 16)
                    spareBits = infoByte & 0b00000111
                    ci = infoByte >> 3 & 0b00000001
                    dcs = infoByte >> 4 & 0b00000111
                    if dcs != 0x00:
                        raise Exception("Only GSM coding is supported in DCS")
                    ext = infoByte >> 7 & 0b00000001
                else:
                    spareBits = len(shortName) % 8
                    ci = 0 #don't add the letters for the Country's Initials
                    dcs = 0 #GSM
                    ext = 1 #?
                    infoByte = ext << 7 | dcs << 3 | ci << 2 | spareBits
                shortNameGsm7 = "%02X%s" %(infoByte, shortNameGsm7)
                types.addTlv(tmpData, types.SHORT_NW_NAME_TAG, hextools.hex2bytes(shortNameGsm7))
            if additionalInfo:
                types.addTlv(tmpData, types.ADDITIONAL_INFORMATION_PLMN_TAG, hextools.hex2bytes(additionalInfo))
            dataNew += "%s;" %hextools.bytes2hex(tmpData)
        return dataNew

    def getEfOpl(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            if not record:
                continue
            binRecord = hextools.hex2bytes(record)
            if binRecord.count(0xFF) == len(binRecord):
                continue
            lai = hextools.bytes2hex(binRecord[0:7])
            mccMnc = hextools.decode_BCD(hextools.hex2bytes(lai)[0:3])
            lacStart = lai[6:10]
            lacEnd = lai[10:14]
            lacRange = "%s-%s" %(lacStart, lacEnd)
            pnnId = binRecord[7]
            dataNew += "mcc_mnc=%s,lac=%s,pnnId=%d;" %(mccMnc, lacRange, pnnId)
        return dataNew

    def setEfOpl(self, data):
        data = data.split(';')
        dataNew = ''
        for record in data:
            if not record:
                continue
            mccMnc = types.getParamValue(record, "mcc_mnc")
            if not mccMnc:
                raise Exception("mcc_mnc not provided")
            if len(mccMnc) != 6:
                mnc3 = 'F'
            else:
                mnc3 = mccMnc[5]
            mccMnc = "%s%s%s" %(mccMnc[0:3], mnc3, mccMnc[3:5])
            lacRange = types.getParamValue(record, "lac")
            if not lacRange:
                lacRange = '0000-FFFE'
            lacStart = lacRange.split("-")[0]
            lacEnd = lacRange.split("-")[1]
            pnnId = int(types.getParamValue(record, "pnnId"), 16)
            lai = "%s%04X%04X" %(hextools.bytes2hex(hextools.encode_BCD(mccMnc)), int(lacStart, 16), int(lacEnd, 16))
            dataNew += "%s%02X;" %(lai, pnnId)
        return dataNew

    def fileHandler(self, mode, fileName, data):
        fileName = fileName.replace("EF_", '')
        #remove forbidden characters in function name
        fileName = fileName.replace("-", '')
        fileName = fileName.lower()
        fileName = "%s%s" %(fileName[0].upper(), fileName[1:])
        if mode == MODE_GET:
            prefix = "get"
        else:
            prefix = "set"
        functionName = "%sEf%s" %(prefix, fileName)
        try:
            handler = getattr(self, functionName)
        except:
            raise Exception("Add method '%s' in file %s" %(functionName, __file__))
        return handler(data)

    def getFileValue(self, fileName, data):
        return self.fileHandler(MODE_GET, fileName, data)

    def setFileValue(self, fileName, data):
        return self.fileHandler(MODE_SET, fileName, data)
