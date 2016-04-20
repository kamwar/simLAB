#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Kamil Wartanowicz

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from sim import sim_router
from sim import sim_card
from sim import sim_shell
from util import hextools
from util import types_g
from util import types
import unittest
import logging

from sim import sim_reader
from sim import sim_ctrl_2g
from sim import sim_ctrl_3g

MODE_SIM = sim_reader.MODE_PYSCARD
SIM_TYPE = types.TYPE_USIM

class TestSimShell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simCard = sim_card.SimCard(mode=MODE_SIM)
        cls.simCard.removeAllReaders()
        try:
            cls.simCard.connect(0)
        except Exception as e:
            if "no card in reader" in str(e):
                cls.simCard.stop()
                raise Exception("No card in reader")
        cls.simRouter = sim_router.SimRouter(cards=[cls.simCard], type=SIM_TYPE, mode=sim_router.SIMTRACE_OFFLINE)
        cls.simRouter.run(mode=sim_router.ROUTER_MODE_DISABLED)
        cls.shell = cls.simRouter.shell

    def test_01_read_iccid(self):
        status, data = self.shell.read("/2FE2")
        self.shell.assertOk(status, data)
        value = types.getDataValue(data)
        valueLength = len(value)
        self.assertGreater(valueLength, 9, "Invalid ICCID length")

    def test_02_read_imsi(self):
        path = "/ADF0/EF_IMSI"
        logging.info("test path: %s" %path)
        status, data1 = self.shell.readi(path)
        self.shell.assertOk(status, data1)
        path = "/7F20/EF_IMSI"
        logging.info("test path: %s" %path)
        status, data2 = self.shell.readi(path)
        self.shell.assertOk(status, data2)
        status, data = self.shell.cd("/")
        self.shell.assertOk(status, data)
        path = "EF_IMSI"
        logging.info("test path: %s" %path)
        status, data3 = self.shell.readi(path)
        self.shell.assertOk(status, data3)
        path = "/ADF_USIM"
        logging.info("test path: %s" %path)
        status, data = self.shell.cd(path)
        self.shell.assertOk(status, data)
        path = "./6F07"
        logging.info("test path: %s" %path)
        status, data4 = self.shell.readi(path)
        self.shell.assertOk(status, data4)
        self.assertEqual(data1, data2)
        self.assertEqual(data1, data3)
        self.assertEqual(data1, data4)

    def test_03_read_imsi_raw(self):
        status, data1 = self.shell.read("/ADF0/EF_IMSI")
        self.shell.assertOk(status, data1)
        status, data = self.shell.cd("/")
        self.shell.assertOk(status, data)
        status, data2 = self.shell.read("EF_IMSI")
        self.shell.assertOk(status, data2)
        imsi1 = types.getDataValue(data1)
        imsi2 = types.getDataValue(data2)
        self.assertEqual(imsi1, imsi2)
        imsiRawLength = len(imsi1)
        self.assertGreater(imsiRawLength, 14+3, "Invalid imsi raw length")

    def test_04_get_plmn(self):
        status, data1 = self.shell.get_plmn()
        self.shell.assertOk(status, data1)
        self.assertGreaterEqual(len(data1), 5*2)
        self.assertLessEqual(len(data1), 6*2)
        status, data2 = self.shell.readi("EF_IMSI")
        self.shell.assertOk(status, data2)
        self.assertTrue(data1 in data2)

    def test_05_read_arr(self):
        status, data = self.shell.read("/2F06")
        self.shell.assertOk(status, data)

    def test_06_create_file(self):
        # Create DF and EF using absolute paths
        dirPath = "/DEAD/"
        try:
            self.shell.delete(dirPath)
        except:
            pass
        status, out = self.shell.create(dirPath)
        self.shell.assertOk(status, out)
        status, out = self.shell.delete(dirPath)
        self.shell.assertOk(status, out)

        dirPath = "/ADF0/DEAD/"
        filePath = "/ADF0/DEAD/BEEF"
        try:
            self.shell.delete(dirPath)
        except:
            pass
        status, out = self.shell.create(dirPath)
        self.shell.assertOk(status, out)
        status, out = self.shell.create(filePath)
        self.shell.assertOk(status, out)
        status, out = self.shell.delete(filePath)
        self.shell.assertOk(status, out)
        status, out = self.shell.delete(dirPath)
        self.shell.assertOk(status, out)

    def test_07_create_file_relative(self):
        # Create DF and EF using relative paths
        dirPath = "./DEAD/"
        filePath = "./BEEF"
        dirPath2 = "./DEAF/"
        try:
            self.shell.delete(dirPath)
        except:
            pass
        status, out = self.shell.create(dirPath)
        self.shell.assertOk(status, out)
        status, out = self.shell.create(filePath)
        self.shell.assertOk(status, out)
        status, out = self.shell.create(dirPath2)
        self.shell.assertOk(status, out)
        status, out = self.shell.create(filePath)
        self.shell.assertOk(status, out)

        status, out = self.shell.delete(dirPath2)
        self.shell.assertOk(status, out)
        status, out = self.shell.delete(dirPath)
        self.shell.assertOk(status, out)

    def test_08_create_adf(self):
        # Get number of EF_DIR records
        status, data = self.shell.read("/2F00")
        self.shell.assertOk(status, data)
        numOfRecords = len(data.split(';')) - 1
        # Use the next free Id
        dirPath = "/ADF%d/" % numOfRecords
        try:
            self.shell.delete(dirPath)
        except:
            pass
        status, out = self.shell.create(dirPath)
        if status == "status NOK":
            raise unittest.SkipTest(
                """Known issue: ADF creation doesn't work for some SIM cards
                 (INCORRECT_PARAMETER_IN_DATA_FIELD is returned)""")
        #self.shell.assertOk(status, out)
        status, out = self.shell.delete(dirPath)
        self.shell.assertOk(status, out)

    def test_09_pwd(self):
        dirPath = "/7F10/5F3A"
        name = "DF_PHONEBOOK"
        status, out = self.shell.cd(dirPath)
        self.shell.assertOk(status, out)
        status, out = self.shell.pwd()
        self.shell.assertOk(status, out)
        path = types.getDataValue(out)
        #compare to directory
        self.assertEqual(path, "path=%s/,name=%s,simId=0" %(dirPath, name))

    def test_10_ls(self):
        dirPath = "/"
        status, out = self.shell.cd(dirPath)
        self.shell.assertOk(status, out)
        status, out = self.shell.ls()
        self.shell.assertOk(status, out)
        files = types.getDataValue(out)
        self.assertTrue(files)
        dirPath = "/7F10"
        status, out = self.shell.cd(dirPath)
        self.shell.assertOk(status, out)
        status, out = self.shell.ls()
        self.shell.assertOk(status, out)
        files = types.getDataValue(out)
        self.assertTrue("5F3A/" in files, "Files: %s" %files)

    def test_11_resize(self):
        filePath = "/ADF0/DEAD/BEEF"
        parentPath = types.parentDirFromPath(filePath) + '/'
        # Cleanup
        try:
            self.shell.delete(parentPath)
        except:
            pass
        # Create temporary dir and file (linear)
        fileType = types_g.fileDescriptor.LINEAR_FIXED_STRUCTURE
        fileSize = 0x30
        recordLength = 0x10
        status, out = self.shell.create(filePath,
                        "fileType=%X,fileSize=%X,recordLength=%X" \
                            % (fileType, fileSize, recordLength))
        self.shell.assertOk(status, out)
        # Increase the size of the file (by 2 new records) with a pattern
        newFileSize = fileSize + recordLength * 2
        pattern = types.addTrailingBytes('', 0xA5, recordLength-4) # not the whole record length
        status, out = self.shell.resize(filePath, hex(newFileSize), pattern)
        self.shell.assertOk(status, out)
        # Check the data after resize
        status, data = self.shell.read(filePath)
        self.shell.assertOk(status, data)
        value = types.getDataValue(data).replace(';', '')
        self.assertEqual(len(value)/2, newFileSize)
        # Decrease the size of the file to one record
        status, out = self.shell.resize(filePath, hex(recordLength))
        self.shell.assertOk(status, out)

        status, out = self.shell.delete(parentPath)
        self.shell.assertOk(status, out)

    @unittest.skip("The EXTEND command is probably only supported by Gemalto")
    def test_12_extend(self):
        filePath = "/ADF0/DEAD/BEEF"
        parentPath = types.parentDirFromPath(filePath) + '/'
        # Cleanup
        try:
            self.shell.delete(parentPath)
        except:
            pass
        # Create temporary dir and file (linear)
        fileType = types_g.fileDescriptor.LINEAR_FIXED_STRUCTURE
        fileSize = 0x30
        recordLength = 0x10
        status, out = self.shell.create(filePath,
                        "fileType=%X,fileSize=%X,recordLength=%X" \
                            % (fileType, fileSize, recordLength))
        self.shell.assertOk(status, out)
        # Increase the size of the file (by 2 new records) with a pattern
        numOfRecordsToExtend = 2
        status, out = self.shell.extend(filePath, numOfRecordsToExtend)
        self.shell.assertOk(status, out)
        # Check the data after extension
        status, data = self.shell.read(filePath)
        self.shell.assertOk(status, data)
        value = types.getDataValue(data).replace(';', '')
        self.assertEqual(len(value)/2, fileSize + numOfRecordsToExtend * recordLength)

        status, out = self.shell.delete(parentPath)
        self.shell.assertOk(status, out)

    @classmethod
    def tearDownClass(cls):
        cls.simCard.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    unittest.main()