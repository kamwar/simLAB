#!/usr/bin/python
# LICENSE: GPL2
# (c) 2013 Tom Schouten <tom@getbeep.com>
# (c) 2014, Kamil Wartanowicz <k.wartanowicz@gmail.com>

import logging
import os
import threading
import time

import usb
import plac

import sim_shell
import sim_ctrl_2g
import sim_ctrl_3g
import sim_reader
import sim_card

from util import types_g
from util import types
from util import hextools

ROUTER_MODE_DISABLED = 0
ROUTER_MODE_INTERACTIVE = 1
ROUTER_MODE_TELNET = 2
ROUTER_MODE_DBUS = 3

_version_ = 1.1

# SIMtrace slave commands and events, see iso7816_slave.h
CMD_SET_ATR  = 0
CMD_SET_SKIP = 1
CMD_HALT     = 2
CMD_POLL     = 3
CMD_R_APDU   = 4

# TODO: check why this event is received, at best remove it
EVT_UNKNOWN  = 0
EVT_RESET    = 2
EVT_C_APDU   = 4

SIMTRACE_OFFLINE = 0
SIMTRACE_ONLINE = 1

MAIN_INTERFACE = 0
CTRL_INTERFACE = 1

INJECT_READY = 0
INJECT_NO_FORWARD = 1
INJECT_WITH_FORWARD = 2
INJECT_RESET = 3

TRY_ANOTHER_CARD_ON_AUTH_FAILURE = True

LOG_NONE_APDU_IN_FILE = True


class SimRouter(object):
    def __init__(self,
                 cards,
                 atr=None,
                 type=types.TYPE_USIM,
                 mode=SIMTRACE_ONLINE):
        self.loggingApdu = self.setupLogger()
        if LOG_NONE_APDU_IN_FILE:
            self.logging = self.loggingApdu
        else:
            self.logging = logging
        self.atr = atr
        self.simType = type
        self.mode = mode

        self.cardsDict = self.addControlCard(cards)
        self.lastUpdate = 0

        self.apduInjectedCard = None
        self.apduInjectedData = None
        self.interpreter = None
        self.routerMode = ROUTER_MODE_DISABLED

        if self.mode != SIMTRACE_OFFLINE:
            self.dev = self.usb_find(0x03eb, 0x6119)
            if self.dev is None:
                self.logging.warning("Simtrace not connected!")
                self.mode = SIMTRACE_OFFLINE
        self.simCtrl = None
        self.loop = None
        self.shell = None
        self.lock = threading.Lock()
        self.rapduInject = None
        self.inject = INJECT_READY

    def addControlCard(self, cards):
        cardDicts = []
        for cardMain in cards:
            cardCtrl = sim_card.SimCard(mode=cardMain.mode, type=self.simType)
            if cardMain.mode == sim_reader.MODE_SIM_SOFT:
                #TODO: try to remove
                cardCtrl.simReader = cardMain.simReader

            #TODO: reimplement to not copy all parameter
            cardCtrl.index = cardMain.index
            cardCtrl.atr = cardMain.atr
            #cardCtrl.swNoError = cardMain.swNoError
            cardCtrl.type = cardMain.type
            cardCtrl.logicalChannelClosed = cardMain.logicalChannelClosed

            # Do not apply ins and file forwarding rules on control interface.
            cardCtrl.removeRoutingAttr()
            cardDict = {MAIN_INTERFACE : cardMain, CTRL_INTERFACE : cardCtrl}
            cardDicts.append(cardDict)
        return cardDicts

    def usbCtrlOut(self, req, buf):
        if self.mode == SIMTRACE_OFFLINE:
            return []
        return self.dev.ctrl_transfer(0x40,
                                  bRequest=req,    # R-APDU
                                  data_or_wLength=buf,
                                  timeout=500)

    def usbCtrlIn(self, req):
        return self.dev.ctrl_transfer(0xC0,
                                  bRequest=req,
                                  data_or_wLength=512,
                                  timeout=512)

    def receiveData(self, cmd):
        if self.mode == SIMTRACE_OFFLINE:
            return []
        try:
            return self.usbCtrlIn(cmd)
        except:
            time.sleep(0.2)
            return self.usbCtrlIn(cmd)

    def sendData(self, msg):
        return self.usbCtrlOut(CMD_R_APDU, msg)

    def resetCards(self, soft=True):
        if soft:
            resetThread = ResetThread(self)
            resetThread.setDaemon(True)
            # Start handling C-APDUs.
            resetThread.start()
        else:
            for cardDict in self.cardsDict:
                cardDict[MAIN_INTERFACE].reset()

    def receiveCommandApdu(self):
        msg = []
        # FIXME: This is the main event loop.  Move it to top level.
        msg = list(self.receiveData(CMD_POLL))
        if not len(msg):
            return None, None
        data = None
        evt = msg[0]
        if evt == EVT_C_APDU:
            data = msg[4:]
        elif evt == EVT_RESET:
            pass
        elif evt == EVT_UNKNOWN:
            return None, None
        else:
            self.loggingApdu.info("unknown event: %s\n" % hextools.bytes2hex(msg))
        return (evt, data)

    def sendResponseApdu(self, msg):
        self.sendData(msg)

    def command(self, tag, payload=[]):  # dummy byte
        self.loggingApdu.debug("CMD %d %s" % (tag, hextools.bytes2hex(payload)))
        self.usbCtrlOut(tag, payload)

    def aidCommon(self, card):
        if not card.routingAttr:
            return False
        return set(sim_card.FILES_AID).issubset(set(card.routingAttr.filesCommon))

    def getSoftCardDict(self):
        for cardDict in self.cardsDict:
            if cardDict[MAIN_INTERFACE].mode == sim_reader.MODE_SIM_SOFT:
                return cardDict
        return None

    def getFileHandler(self, file):
        #by default execute apdu in card 0
        cards = [self.cardsDict[0][MAIN_INTERFACE]]

        for cardDict in self.cardsDict:
            if cardDict == self.cardsDict[0]:
                #cardDict already in cards
                continue
            card = cardDict[MAIN_INTERFACE]
            if file in card.routingAttr.filesCommon:
                cards.append(card)
            elif file in card.routingAttr.filesReplaced:
                return [card]
        return cards

    def getInsHandler(self, ins, apdu):
        #by default execute apdu in card 0
        cards = [self.cardsDict[0][MAIN_INTERFACE]]

        for cardDict in self.cardsDict:
            if cardDict == self.cardsDict[0]:
                #cardDict already in cards
                continue
            card = cardDict[MAIN_INTERFACE]
            if (ins == 'GET_RESPONSE' and
                card.routingAttr.getFileSelected(apdu[0]) == 'AUTH' and
                'INTERNAL_AUTHENTICATE' in card.routingAttr.insReplaced):
                return [card]
            elif ins in card.routingAttr.insCommon:
                if (ins in ['GET_RESPONSE','SELECT_FILE'] and
                      card.routingAttr.getFileSelected(apdu[0]) in card.routingAttr.filesReplaced):
                    cards.insert(0, card)
                else:
                    cards.append(card)
            elif ins in card.routingAttr.insReplaced:
                if ins == 'INTERNAL_AUTHENTICATE':
                    card.routingAttr.setFileSelected('AUTH', apdu[0])
                return [card]
        return cards

    def addLeftHandlers(self, cards):
        for cardDict in self.cardsDict:
            card = cardDict[MAIN_INTERFACE]
            if card in cards:
                continue
            cards.append(card)
        return cards

    def getHandlers(self, apdu, inject=None):
        cardsData = []

        if inject == INJECT_NO_FORWARD:
            if self.apduInjectedCard:
                cardsData.append([self.apduInjectedCard, 0])
            else:
                cardsData.append([self.getCtrlCard(0), 0])
            return cardsData

        ins = types.insName(apdu)

        if ins == 'SELECT_FILE':
            for cardDict in self.cardsDict:
                card = cardDict[MAIN_INTERFACE]
                #TODO: handle read/write/update command with SFI in P1
                card.routingAttr.setFileSelected(self.fileName(apdu), apdu[0])
        if ins in sim_card.FILE_INS:
            cards = self.getFileHandler(self.cardsDict[0][MAIN_INTERFACE].routingAttr.getFileSelected(apdu[0]))
        else:
            cards = self.getInsHandler(ins, apdu)

        i = 0;
        forwardApdu = True
        for card in cards:
            if i != 0:
                forwardApdu = False
            cardsData.append([card, forwardApdu])
            i += 1
        return cardsData

    def handleApdu(self, cardData, apdu):
        card = cardData[0]
        sendData = cardData[1]

        if card == None:
            raise Exception("card not initialized")

        ins = types.insName(apdu)

        if card != self.getMainCard(0):
            origApdu = apdu
            if ( self.aidCommon(card) and
                 card.routingAttr.aidToSelect and
                 self.getMainCard(0).routingAttr.aidToSelect == hextools.bytes2hex(apdu) and #origin apdu is AID
                 int(card.routingAttr.aidToSelect[0:2], 16) == apdu[0]): #check the same class
                apdu = hextools.hex2bytes(card.routingAttr.aidToSelect)
                card.routingAttr.aidToSelect = None
            elif ( self.aidCommon(card) and
                   card.routingAttr.getFileSelected(apdu[0]) == 'EF_DIR' and
                   ins == 'READ_RECORD' and
                   card.routingAttr.recordEfDirLength):
                apdu[4] = card.routingAttr.recordEfDirLength

            if origApdu != apdu:
                self.loggingApdu.info("")
                self.loggingApdu.info("*C-APDU%d: %s" %(self.getSimId(card), hextools.bytes2hex(apdu)))

        if self.simType == types.TYPE_SIM and (apdu[0] & 0xF0) != 0xA0:
            #force 2G on USIM cards
            sw = types_g.sw.CLASS_NOT_SUPPORTED
            sw1 = sw>>8
            sw2 = sw & 0x00FF
            responseApdu = [sw1, sw2]
        elif ins == 'GET_RESPONSE' and card.routingAttr.getResponse:
            responseApdu = card.routingAttr.getResponse
            card.routingAttr.getResponse = None
        else:
            responseApdu = card.apdu(apdu)

        if card != self.getMainCard(0):
            if (self.aidCommon(card) and
                    card.routingAttr.getFileSelected(apdu[0]) == 'EF_DIR' and
                    ins == 'GET_RESPONSE' and
                    types.swNoError(responseApdu) and
                    len(responseApdu) > 7):
                card.routingAttr.recordEfDirLength = responseApdu[7]

        if (TRY_ANOTHER_CARD_ON_AUTH_FAILURE and
                self.getNbrOfCards() > 1 and
                card.routingAttr.getFileSelected(apdu[0]) == 'AUTH' and
                types.sw(responseApdu) == types_g.sw.AUTHENTICATION_ERROR_APPLICATION_SPECIFIC):
            sw1Name, swName = types.swName(types.sw(responseApdu) >> 8, types.sw(responseApdu) & 0x00FF)
            self.logging.warning("Response not expected. SW1: %s, SW: %s" %(sw1Name, swName))
            self.logging.warning("Change card to process AUTHENTICATION")
            if card == self.getMainCard(0):
                cardTmp = self.getMainCard(1)
            else:
                cardTmp = self.getMainCard(0)
            responseApdu = cardTmp.apdu(apdu)
            cardTmp.routingAttr.setFileSelected('AUTH', apdu[0])
            card.routingAttr.setFileSelected(None, apdu[0])
            # TODO: check if exist
            cardTmp.routingAttr.insReplaced.append('INTERNAL_AUTHENTICATE')
            if types.sw1(responseApdu) in [types_g.sw1.RESPONSE_DATA_AVAILABLE_2G, types_g.sw1.RESPONSE_DATA_AVAILABLE_3G]:
                # cache 'GET_RESPONSE'
                getResponseLength = types.sw2(responseApdu)
                cla = apdu[0]
                apduTmp = "%02XC00000%02X" %(cla, getResponseLength)
                self.loggingApdu.info("**C-APDU%d: %s" %(self.getSimId(cardTmp), apduTmp))
                cardTmp.routingAttr.getResponse = cardTmp.apdu(apduTmp)

        if card.routingAttr.getFileSelected(apdu[0]) == 'EF_IMSI' and types.swNoError(responseApdu):
            #cache imsi
            responseData = types.responseData(responseApdu)
            if ins == 'READ_BINARY' and types.p1(apdu) == 0 and types.p2(apdu) == 0:
                #When P1=8X then SFI is used to select the file.
                #Remove the check when SFI checking is implemented
                imsi = hextools.decode_BCD(responseData)[3:]
                #TODO: remove length check when name for the file comes from
                #the whole path and not fid. 6f07 is also in ADF_ISIM
                if len(imsi) > 10:
                    card.imsi = imsi
                    #update associated interface
                    if self.isCardCtrl(card):
                        self.getRelatedMainCard(card).imsi = imsi
                    else:
                        self.getRelatedCtrlCard(card).imsi = imsi
            elif ins == 'UPDATE_BINARY':
                card.imsi = None

        responseApduHex = hextools.bytes2hex(responseApdu)
        #example of APDU modification
        if responseApduHex == "02542D4D6F62696C652E706CFFFFFFFFFF9000":
            #change SPN name 'T-mobile.pl' for 'Tmobile-SPN'
            responseApdu = hextools.hex2bytes("02546D6F62696C652D53504EFFFFFFFFFF9000")

        if sendData:
            if ((types.sw(responseApdu) == types_g.sw.NO_ERROR or
                 types.sw1(responseApdu) == types_g.sw1.NO_ERROR_PROACTIVE_DATA) and
                 self.getNbrOfCards() > 1):
                # Check for pending SAT command
                for cardDict in self.cardsDict:
                    cardTmp = cardDict[MAIN_INTERFACE]
                    if card == cardTmp:
                        continue
                    if set(sim_card.SAT_INS) <= set(cardTmp.routingAttr.insReplaced):
                        swNoError = cardTmp.swNoError
                        if types.unpackSw(swNoError)[0] == types_g.sw1.NO_ERROR_PROACTIVE_DATA:
                            #update r-apdu with proactive data information
                            responseApdu[-2] = swNoError >> 8
                            responseApdu[-1] = swNoError & 0x00FF
                        break
            self.sendResponseApdu(responseApdu)
        if card == self.getMainCard(0) or sendData:
            self.pretty_apdu(apdu)
        responseApduHex = hextools.bytes2hex(responseApdu)
        self.loggingApdu.info("R-APDU%d: %s" %(self.getSimId(card), responseApduHex))
        # gsmtap.log(apdu,responseApdu) # Uncomment for wireshark
        return responseApdu

    def updateHandler(self, cardData, apdu, rapdu):
        if ( self.aidCommon(cardData[0]) and not
                cardData[0].routingAttr.aidToSelect and
                cardData[0].routingAttr.getFileSelected(apdu[0]) == 'EF_DIR' and
                types.insName(apdu) == 'READ_RECORD' and
                len(rapdu) > 3 and rapdu[3] != 0xFF and
                types.swNoError(rapdu)):
            # keep the same class - apdu[0], change length and avalue of selected AID
            cardData[0].routingAttr.aidToSelect = "%02XA40404%s" %(apdu[0], hextools.bytes2hex(rapdu[3 : (rapdu[3] + 4)]))

        if types.sw1(rapdu) in [types_g.sw1.RESPONSE_DATA_AVAILABLE_2G, types_g.sw1.RESPONSE_DATA_AVAILABLE_3G]:
            # cache 'GET_RESPONSE'
            getResponseLength = types.sw2(rapdu)
            cla = apdu[0]
            apdu = "%02XC00000%02X" %(cla, getResponseLength)
            cardData[0].routingAttr.getResponse = cardData[0].apdu(apdu)

    def tick(self):
        with self.lock:
            inject = INJECT_READY
            evt, apdu = self.receiveCommandApdu()
            if evt == EVT_RESET:
                self.resetCards()
                return
            if not apdu:
                if (not self.inject or
                        self.rapduInject):  # Wait until rapduInject is consumed
                    return
                else:
                    inject = self.inject
                    apdu = self.apduInjectedData
                    self.apduInjectedData = None
            if not apdu:
                raise Exception("APDU is empty")
            self.lastUpdate = time.time()
            cardsData = self.getHandlers(apdu, inject)
            responseApdu = None
            for cardData in cardsData:
                if cardData == cardsData[0]:
                    apduHex = hextools.bytes2hex(apdu)
                    self.loggingApdu.info("")
                    self.loggingApdu.info("C-APDU%d: %s" %(self.getSimId(cardData[0]), apduHex))
                responseApduTemp = self.handleApdu(cardData, apdu)
                if cardData[1]:
                    if cardData[0] != self.getMainCard(0):
                        self.loggingApdu.info("*R-APDU%d" %self.getSimId(cardData[0]))
                    responseApdu = responseApduTemp
                self.updateHandler(cardData, apdu, responseApduTemp)
            if not responseApdu and not inject:
                raise Exception("No response received")
            if inject:
                self.rapduInject = responseApduTemp

    def mainloop(self):
        while 1:
            if self.mode == ROUTER_MODE_DBUS:
                import gevent
                gevent.sleep(0.001)
            self.tick()
            if time.time() - self.lastUpdate > 0.1:
                time.sleep(0.1)

    def getNbrOfCards(self):
        return len(self.cardsDict)

    def getSimId(self, card):
        i = 0
        for cardDict in self.cardsDict:
            if card in [cardDict[MAIN_INTERFACE], cardDict[CTRL_INTERFACE]]:
                return i
            i += 1
        raise Exception("Card not found")

    def getCardDictFromId(self, simId):
        if simId >= self.getNbrOfCards() or simId < 0:
            raise Exception("simId: " + str(simId) + " not found")
        return self.cardsDict[simId]

    def isCardCtrl(self, card):
        for cardDict in self.cardsDict:
            if cardDict[CTRL_INTERFACE] == card:
                return True
        return False

    def getMainCard(self, simId):
        cardDict = self.getCardDictFromId(simId)
        return cardDict[MAIN_INTERFACE]

    def getCtrlCard(self, simId):
        cardDict = self.getCardDictFromId(simId)
        return cardDict[CTRL_INTERFACE]

    def getRelatedMainCard(self, cardCtrl):
        for cardDict in self.cardsDict:
            if cardDict[CTRL_INTERFACE] == cardCtrl:
                return cardDict[MAIN_INTERFACE]
        return None

    def getRelatedCtrlCard(self, cardMain):
        for cardDict in self.cardsDict:
            if cardDict[MAIN_INTERFACE] == cardMain:
                return cardDict[CTRL_INTERFACE]
        return None

    def swapCards(self, simId1, simId2):
        cardDict1 = self.getCardDictFromId(simId1)
        cardDict2 = self.getCardDictFromId(simId2)
        #with self.lock:
        self.cardsDict[simId1] = cardDict2
        self.cardsDict[simId2] = cardDict1

    def copyFiles(self, cardMainFrom, cardMainTo, files):
        simIdFrom = self.getSimId(self.getRelatedCtrlCard(cardMainFrom))
        simIdTo = self.getSimId(self.getRelatedCtrlCard(cardMainTo))
        self.shell.select_sim_card(simIdFrom)
        fileDict = {}
        for file in files:
            status, data = self.shell.read(file)
            self.shell.assertOk(status, data)
            value = types.getDataValue(data)
            fileDict.update({file : value})
        self.shell.select_sim_card(simIdTo)
        for fileName, value in fileDict.iteritems():
            status, data = self.shell.write(fileName, value)
            self.shell.assertOk(status, data)

    def getATR(self):
        if self.atr is not None:
            return self.atr
        else:
            return self.getMainCard(0).getATR()

    def waitInjectReady(self, timeout=15):
        startTime = time.time()
        while True:
            with self.lock:
                if self.inject == INJECT_READY and not self.rapduInject:
                    break
                currentTime = time.time()
                if currentTime - startTime > timeout: #sec
                    if self.rapduInject:
                        logging.error("RAPDU injected response not consumed")
                    self.logging.error("Timeout. Previous apdu injected has not finished within %ds" %timeout)
                    self.rapduInject = None
                    self.inject = INJECT_READY
                    break
            time.sleep(0.001)

    def waitRapduInject(self, timeout=30):
        startTime = time.time()
        while True:
            with self.lock:
                rapduInject = self.rapduInject
                if rapduInject:
                    self.rapduInject = None
                    self.inject = INJECT_READY
                    return rapduInject
                currentTime = time.time()
                if currentTime - startTime > timeout:
                    self.inject = INJECT_READY
                    raise Exception("Timeout. No rapdu for injected data received within %ds" %timeout)
            time.sleep(0.001)

    def injectApdu(self, apdu, card, mode=INJECT_NO_FORWARD):
        # TODO: add inject tag to logs
        self.waitInjectReady()
        with self.lock:
            self.apduInjectedCard = card
            self.apduInjectedData = hextools.hex2bytes(apdu)
            self.inject = mode
        return self.waitRapduInject()

    def setPowerSkip(self, skip):
        self.command(CMD_SET_SKIP, hextools.u32(skip))

    def powerHalt(self):
        self.command(CMD_HALT)

    def run(self, mode=ROUTER_MODE_INTERACTIVE):
        if self.loop and self.routerMode == ROUTER_MODE_DISABLED:
            self.shell.updateInteractive(self.getInteractiveFromMode(mode))
            self.startPlacServer(mode)
            return
        self.routerMode = mode
        time.sleep(0.1)  # Truncated logs
        self.loggingApdu.info("============")
        self.loggingApdu.info("== simLAB ==")
        self.loggingApdu.info("== ver %s==" %_version_)
        self.loggingApdu.info("============")
        self.command(CMD_SET_ATR, self.getATR())
        self.setPowerSkip(skip=1)
        self.powerHalt()
        self.loop = MainLoopThread(self)
        self.loop.setDaemon(True)
        # Start handling incoming phone C-APDUs.
        self.loop.start()
        # Default card control interface.
        if self.simType == types.TYPE_SIM:
            self.simCtrl = sim_ctrl_2g.SimCtrl(self)
        else:
            self.simCtrl = sim_ctrl_3g.SimCtrl(self)
        self.simCtrl.init()
        interactive = self.getInteractiveFromMode(mode)
        # Plac telnet server works without interactive mode
        self.shell = sim_shell.SimShell(self.simCtrl, interactive)
        self.startPlacServer(mode)

    def getInteractiveFromMode(self, mode):
        if mode in [ROUTER_MODE_INTERACTIVE, ROUTER_MODE_DBUS]:
            return True
        return False

    def startPlacServer(self, mode):
        if mode  == ROUTER_MODE_DISABLED:
            return
        self.interpreter = plac.Interpreter(self.shell)
        if mode == ROUTER_MODE_TELNET:
            self.interpreter.start_server() # Loop
        elif mode == ROUTER_MODE_DBUS:
            from util import dbus_ctrl
            dbus_ctrl.startDbusProcess(self) # Loop
        elif mode == ROUTER_MODE_INTERACTIVE:
            path = self.simCtrl.getCurrentFile().path
            self.interpreter.interact(prompt="\n%s>"%path)
        else:
            raise Exception("Unexpected mode")

    def setShellPrompt(self, prompt):
        if self.interpreter != None:
            self.interpreter.prompt = prompt

    def setupLogger(self):
        logger = logging.getLogger("router")
        #dont't propagate to root logger
        logger.propagate=False
        logger.handlers = []

        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        dir = os.path.dirname(__file__)
        resultFile = dir + "/../apdu.log"
        fileHandler = logging.FileHandler(resultFile, mode='w')
        fileHandler.setLevel(logging.INFO)

        # create formatter and add it to the handlers
        consoleFormatter = logging.Formatter(fmt='%(message)s')
        fileFormatter = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt='%H:%M:%S')

        consoleHandler.setFormatter(consoleFormatter)
        fileHandler.setFormatter(fileFormatter)

        # add the handlers to the logger
        logger.addHandler(consoleHandler)
        logger.addHandler(fileHandler)

        if extHandler:
            #add handler for test runner
            logger.addHandler(extHandler)
        return logger

    def fileName(self, apdu):
        if types.p1(apdu) != types.SELECT_BY_DF_NAME:
            fid = types.fileId(apdu)
            fid = "%04X" %fid
            if fid == "7FFF":
                return "ADF"
            try:
                fileName = self.simCtrl.simFiles.getNameFromFid(fid)
            except:
                #TODO: try to remove
                fileName = fid
        else:
            # AID
            fileName = hextools.bytes2hex(types.aid(apdu)) #'A000'
        return fileName

    def pretty_apdu(self, apdu):
        str = types.insName(apdu)
        if str == 'SELECT_FILE':
            str += " " + self.fileName(apdu)
        self.loggingApdu.info(str)

    def usb_find(self, idVendor, idProduct):
        LIBUSB_PATH = "/usr/lib/libusb-1.0.so"
        try:
            dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        except:
            backend = usb.backend.libusb1.get_backend(find_library=lambda x: LIBUSB_PATH)
            if not backend:
                logging.error("libusb-1.0 not found")
                return None
            dev = usb.core.find(idVendor=idVendor, idProduct=idProduct, backend=backend)
        return dev

extHandler = None
def setLoggerExtHandler(handler):
    global extHandler
    extHandler = handler


class MainLoopThread(threading.Thread):
    def __init__(self, simRouter):
        threading.Thread.__init__(self)
        self.simRouter = simRouter
        threading.Thread.setName(self, 'MainLoopThread')
        self.__lock = threading.Lock()

    def run(self):
        self.__lock.acquire()
        for cardDict in self.simRouter.cardsDict:
            if cardDict[MAIN_INTERFACE].mode == sim_reader.MODE_SIM_SOFT:
                # Set SimRouter class in SatCtrl.
                card = cardDict[CTRL_INTERFACE].simReader.getHandler().getCard(cardDict[CTRL_INTERFACE].index)
                card.satCtrl.setSimRouter(self.simRouter)
        self.simRouter.mainloop()
        self.__lock.release()

    def stop(self):
        self.join()

class ResetThread(threading.Thread):
    def __init__(self, simRouter):
        threading.Thread.__init__(self)
        self.simRouter = simRouter
        threading.Thread.setName(self, 'ResetThread')
        self.__lock = threading.Lock()

    def run(self):
        self.__lock.acquire()
        self.softReset()
        self.__lock.release()


    def softReset(self):
        self.simRouter.logging.info("\n")
        self.simRouter.logging.info("<- Soft reset")
        for cardDict in self.simRouter.cardsDict:
            if (not cardDict[MAIN_INTERFACE].routingAttr or
                    #skip SIM with no common instruction
                    cardDict[MAIN_INTERFACE].routingAttr.insCommon == [] or
                    not self.simRouter.simCtrl):
                continue
            #select MF
            if self.simRouter.simType == types.TYPE_USIM:
                apdu = "00A40004023F00"
            else:
                apdu = "A0A40000023F00"
            rapdu = self.simRouter.injectApdu(apdu, cardDict[MAIN_INTERFACE], mode=INJECT_NO_FORWARD)
            if not rapdu:
                #Skip resetting if there is USB apdu to handle
                self.simRouter.logging.info("Soft reset not completed, USB apdu ongoing")
                return
            # Close opened logical channel so the are not exhousted when UE
            # assign new channels after SIM reset.
            ctrlLogicalChannel = self.simRouter.simCtrl.logicalChannel
            for channel in range(1,4):
                if channel != ctrlLogicalChannel: #skip control logical channel
                    originChannel = 0
                    if self.simRouter.simType == types.TYPE_SIM:
                        cla = 0xA0
                    else:
                        cla = 0x00
                    cla = cla | (originChannel & 0x0F)
                    apdu = "%02X7080%02X00" %(cla, channel)
                    rapdu = self.simRouter.injectApdu(apdu, cardDict[MAIN_INTERFACE], mode=INJECT_NO_FORWARD)
                    if not rapdu:
                        #Skip resetting if there is USB apdu to handle
                        self.simRouter.logging.info("Soft reset not completed, USB apdu ongoing")
                        break
        self.simRouter.logging.info("-> reset end")

    def stop(self):
        self.join()
