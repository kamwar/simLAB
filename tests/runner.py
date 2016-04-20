#!/usr/bin/python
# LICENSE: GPL2
# (c) 2015 Kamil Wartanowicz

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import unittest
import logging
import traceback
from optparse import OptionParser

import html_test_runner
from sim import sim_router

dir = os.path.dirname(__file__)
resultDir = os.path.join(dir, "result")
startDir = dir

def setupLogger(loggingLevel):
    if not os.path.exists(resultDir):
        os.makedirs(resultDir)
    resultFile = os.path.join(resultDir, "result.txt")
    # create logger with 'root'
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(loggingLevel)
    # create file handler which logs even debug messages
    fileHandler = logging.FileHandler(resultFile)
    fileHandler.setLevel(loggingLevel)
    # create console handler with a higher log level
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(loggingLevel)
    # create ext handler with a higher log level
    # use this handler to redirect streaming in html_test_runner
    extHandler = logging.StreamHandler(stream=html_test_runner.stdout_redirector)
    extHandler.setLevel(loggingLevel)
    # create formatter and add it to the handlers
    formatterConsole = logging.Formatter(fmt='%(message)s')
    formatter = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    consoleHandler.setFormatter(formatterConsole)
    fileHandler.setFormatter(formatter)
    extHandler.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fileHandler)
    logger.addHandler(consoleHandler)
    logger.addHandler(extHandler)
    sim_router.setLoggerExtHandler(extHandler)

def startFile(outfile):
    sysName = sys.platform
    if sysName.startswith('java'):
        import java.lang.System
        sysName = java.lang.System.getProperty('os.name').lower()
    if sysName.startswith('linux'):
        osName = "linux"
    elif sysName.startswith('win'):
        osName = "windows"
    if osName == "linux":
        cmd = "/usr/bin/xdg-open "
    elif osName == "windows":
        cmd = "cmd /c START "
    os.system(cmd + outfile.name)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-l", "--logging-level", dest="logging_level",
                help="Logging level, DEBUG=10, INFO=20, WARNING=30, ERROR=40")
    parser.add_option("-s", "--start-directory", dest="start_dir",
                help="Directory to start discovery")
    parser.add_option("-p", "--pattern", dest="pattern",
                help="Pattern to match test files (test*.py default)")
    parser.add_option("-m", "--module-class-test", dest="module_class_test",
                help="Pattern to match specific test/class: module.class.test")
    parser.add_option("-t", "--top-level-directory", dest="top_level_dir",
                help="Top level directory of project (defaults to start directory)")
    parser.add_option("-i", "--iterations", dest="iterations",
                help="Number of iterations")
    (options, args) = parser.parse_args()

    dictArgs = {}
    if options.logging_level:
        loggingLevel = int(options.logging_level)
    else:
        loggingLevel = logging.INFO
    if options.start_dir:
        startDir = options.start_dir
    dictArgs.update({'start_dir':startDir})
    if options.pattern:
        dictArgs.update({'pattern':options.pattern})
    if options.top_level_dir:
        dictArgs.update({'top_level_dir':options.top_level_dir})

    if options.iterations:
        nbrOfiterations = int(options.iterations)
    else:
        nbrOfiterations = 1

    moduleClassTests = []
    if options.module_class_test:
        moduleClassTests = options.module_class_test.split()
    #prevent creating *.pyc files
    sys.dont_write_bytecode = True

    while True:
        setupLogger(loggingLevel)
        infoText = "simLAB test runner: %s" %(" ".join(sys.argv[1:]))
        logging.info(infoText)
        loader = unittest.TestLoader()
        suites = loader.discover(**dictArgs)
        newSuite = unittest.TestSuite()

        for suite in suites._tests:
            new_suite = unittest.TestSuite()
            for _test_group in suite._tests:
                test_group = []
                try:
                    iter(_test_group)
                    test_group = _test_group
                except TypeError:
                    # not iterable, probably module import failure
                    logging.error("Import Failure? class="+_test_group.__class__.__name__+" test="+_test_group._testMethodName)
                    test_group.append(_test_group)
                for test in test_group:
                    if options.module_class_test:
                        # check if any test matches expresion included with '-m' option
                        moduleName = test.__class__.__module__
                        className = test.__class__.__name__
                        testMethodName = test._testMethodName
                        nbrOfModules = len(moduleName.split("."))

                        for moduleClassTest in moduleClassTests:
                            classNameTmp = None
                            testMethodNameTmp = None
                            nbrOfPartsTmp = len(moduleClassTest.split("."))
                            moduleNameTmp = ".".join(moduleClassTest.split(".")[0:nbrOfModules])
                            if nbrOfPartsTmp > nbrOfModules:
                                classNameTmp = moduleClassTest.split(".")[nbrOfModules]
                            else:
                                className = None
                            if nbrOfPartsTmp > nbrOfModules + 1:
                                testMethodNameTmp = moduleClassTest.split(".")[nbrOfModules+1]
                            else:
                                testMethodName = None
                            if (moduleNameTmp == moduleName and
                                classNameTmp == className and
                                testMethodNameTmp == testMethodName):
                                    newSuite.addTest(test)
                            else:
                                #add test to suite in case of import error
                                if className == 'ModuleImportFailure' and moduleClassTest[0] == test._testMethodName:
                                    newSuite.addTest(test)
                        continue
                    newSuite.addTest(test)

        outfile = open(os.path.join(resultDir, "report.html"), "w")
        testRunner = html_test_runner.HTMLTestRunner(
                        stream=outfile,
                        verbosity=2,
                        title='Test Report',
                        description=infoText,
                        )
        testRunner.run(newSuite)
        outfile.close()
        startFile(outfile)

        nbrOfiterations -= 1
        if nbrOfiterations > 0:
            removeModuleSuite(suites)
            continue
        break
