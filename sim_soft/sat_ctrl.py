#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz
# (c) 2014 Szymon Mielczarek
import logging
import threading
# TODO: check why the above import fails
from sat_types import *
from util import types_g
from util import types
from util import hextools
from util import coder


class SatCtrl(object):
    def __init__(self, simType, simXml):
        self.simType = simType
        self.simRouter = None
        self.simXml = simXml
        self.commandNumber = 0x01
        self.proactiveMessage = []
        self.isMessagePending = False
        self.terminalProf = None
        self.responseHandler = []
        self.postActionHandler = []

    def setSimRouter(self, simRouter):
        self.simRouter = simRouter

    def swNoError(self):
        if not self.proactiveMessageAvailable():
            sw = types_g.sw.NO_ERROR
        else:
            sw1 = types_g.sw1.NO_ERROR_PROACTIVE_DATA
            sw2 = self.proactiveMessageLength()
            sw = types.packSw(sw1, sw2)
        return sw

    def terminalProfile(self, apdu):
        data = []

        self.terminalProf = types.dataLc(apdu) # unsed at the moment
        self.createSetupMenu()

        sw = self.swNoError()
        return data, sw

    def terminalResponse(self, apdu):
        data = []

        # get terminal response data
        responseData = types.dataLc(apdu)
        self.handleTerminalResponseData(responseData)

        self.freeCommandId()
        sw = self.swNoError()
        return data, sw

    def handleTerminalResponseData(self, data):
        #"8103012500 02028281 830100":
        # cmd type = 25, qualifier = 0x00, result: '00' - successfull

        ### Parse Command details TLV ###
        commandDetailsData = data[:5] # 5 bytes
        del data[:len(commandDetailsData)]
        cmdType = commandDetailsData[3]
        ### Parse Device identities TLV ###
        deviceIdentitiesData = data[:4] # 4 bytes
        del data[:len(deviceIdentitiesData)]

        ### Parse the Result TLV ###
        data.pop(0) # Result tag
        # The length is coded onto 1 or 2 bytes
        # TS 102 223 V12.1.0 (Annex C)
        length = data.pop(0) # length
        if length == 0x81:  # 2-byte length ?
            length = data.pop(0)
        generalResult = data.pop(0)
        # Display the result info if a command does not performed
        # with a complete success (0x00)
        status = {}
        if generalResult != 0x00:
            logging.info("Result: " + general_result[generalResult])
            status.update({'result' : generalResult})
        """
        For the general results '20', '21','26', '38', '39', '3A', '3C'
        and '3D', it is mandatory for the terminal to provide
        a specific cause value as additional information.
        """
        if length > 1:
            addInfo = data[:length-1]
            # TODO: handle addInfo (8.12.2 - 8.12.13)
            logging.info("Additional information: " + str(addInfo))
            status.update({'information' : addInfo})
            del data[:len(addInfo)]

        ### Parse other TLVs ###
        # Optional information for some specific commands
        tlvTag = None
        respData = data
        if len(data) != 0:
            tlvTag = data.pop(0) # local info tag
            length = data.pop(0) # length
            if length != 0:
                if cmdType == cmd_type.POLL_INTERVAL:
                    return
                elif cmdType == cmd_type.GET_INPUT:
                    respData = self.parseGetInputText(data)
                elif cmdType == cmd_type.SELECT_ITEM:
                    respData = self.parseSelectItemIdentifier(data)
                elif cmdType == cmd_type.PROVIDE_LOCAL_INFO:
                    respData = self.parseLocalInformation(tlvTag, data)
                # and more
        # Handle the reponse
        self.startResponseHandler(status, respData)
        self.runPostActionHandler(status, respData)

    def startResponseHandler(self, status, respData):
        if not len(self.responseHandler):
            return
        handlerDict = self.responseHandler.pop(0)
        handler = handlerDict['handler']
        data = handlerDict['data']
        handler(status, respData, data)

    def runPostActionHandler(self, status, respData):
        if not len(self.postActionHandler):
            return
        handlerDict = self.postActionHandler.pop(0)
        handler = handlerDict['handler']
        data = handlerDict['data']
        self.postHandler = PostHandlerThread(self, handler, status, respData, data)
        self.postHandler.setDaemon(True)
        self.postHandler.start()

    def stopPostActionHandler(self):
        self.postHandler.stop()

    def getTlvData(self, data):
        if not len(data):
            return None
        tlvTag = data.pop(0)
        length = data.pop(0)
        return data[0:length]

    def parseLocalInformation(self, tag, data):
        respData = None
        if tag == comprehension_tag.LOCATION_INFORMATION:
            pass
        elif tag == comprehension_tag.IMEI:
            respData = hextools.decode_BCD(data)[2:]
        # and many more
        return respData

    def parseGetInputText(self, data):
        """Handle Text string"""
        coding = data.pop(0) # TODO: handle coding scheme
        text = hextools.bytes2string(data)
        return text

    def parseSelectItemIdentifier(self, data):
        return (data[0] & 0x7F) # item identifier

    def fetch(self, apdu):
        data = self.proactiveMessage[0 : types.p3(apdu)]
        self.proactiveMessage = []
        self.setMessagePending(False)
        sw = self.swNoError()
        return data, sw

    def envelope(self, apdu):
        data = []

        # get a command from ME/Network
        envelopeData = types.dataLc(apdu)
        self.handleEnvelopeData(envelopeData)

        sw = self.swNoError()
        return data, sw

    def handleEnvelopeData(self, data):
        tag = data.pop(0)
        length = data.pop(0)
        # The length is coded onto 1 or 2 bytes
        # TS 102 223 V12.1.0 (Annex C)
        if length == 0x81:  # 2-byte length ?
            length = data.pop(0)

        if tag == ber_tag.MENU_SELECTION:
            ### Parse Device identities TLV ###
            deviceIdentitiesData = data[:4]  # 4 bytes
            del data[:len(deviceIdentitiesData)]
            ### Parse Item identifier TLV ###
            data.pop(0) # tag
            data.pop(0) # len
            itemID = data.pop(0)
            ### Parse Help request TLV (optional) ###
            helpRequest = False
            if len(data) > 1:
                helpRequest = True
            self.handleMenuSelection(itemID, helpRequest)
        elif tag == ber_tag.CALL_CONTROL:
            """
            For all call set-up attempts the terminal shall first pass
            the call set-up details (dialled digits and associated parameters)
            to the UICC.
            """
            pass
        elif tag == ber_tag.EVENT_DOWNLOAD:
            """
            The terminal informs the UICC if an event previously
            set by a SET UP EVENT LIST proactive command occurs.
            - MT call event
            - Call connected event
            - Call disconnected event
            - Location status event
            etc.
            """
            pass
        elif tag == ber_tag.TIMER_EXPIRATION:
            """
            When a timer previously started by a TIMER MANAGEMENT
            proactive command expires.
            """
            pass

    def handleMenuSelection(self, itemId, helpRequest):
        if not itemId:
            logging.warning("Unexpected ItemId=%02X" %itemId)
            return

        item = "%02X" % itemId
        handler = self.SETUP_MENU_ITEMS[item]['handler']
        #text = self.SETUP_MENU_ITEMS[item]['text']
        handler(self, None) # start action

    def proactiveMessageLength(self):
        return len(self.proactiveMessage)

    def proactiveMessageAvailable(self):
        return self.isMessagePending

    def setMessagePending(self, isPending):
        """If set True it informs that a proactive message
        is available and ready to fetch.
        """
        self.isMessagePending = isPending

    def freeCommandId(self):
        """ For the future possibility of multiple ongoing commands
        (i.e. when the UICC issues further commands before receiving
        the response to the ongoing command)
        """
        if self.commandNumber >= 0xFE:
            self.commandNumber = 0x01
        else:
            self.commandNumber += 1

    def buildProactiveMessage(self, type, qualifier):
        if len(self.proactiveMessage) != 0:
            logging.info("Warning! buildProactiveMessage() called "
            +"while proactiveMessage already present.")

        self.proactiveMessage = [ber_tag.PROACTIVE,
                    0x00, # length will be set later */
                    comprehension_tag.COMMAND_DETAILS ^
                        comprehension_tag.COMPREHENSION_REQUIRED,
                    TLV_COMMAND_DETAILS_LENGTH,
                    self.commandNumber,
                    type,
                    qualifier]

        self.proactiveMessage[1] = len(self.proactiveMessage[2:]) # length
        #self.commandNumber += 1

    def addTagToMessage(self, tag, comprehensionRequired, parameters):
        if len(self.proactiveMessage) == 0:
            logging.info("Warning! addTagToMessage() called while "
            +"proactiveMessage not present.")
            return
        if comprehensionRequired:
            tag ^= comprehension_tag.COMPREHENSION_REQUIRED

        self.proactiveMessage.append(tag)
        self.proactiveMessage.append(len(parameters))
        self.proactiveMessage.extend(parameters)
        self.proactiveMessage[1] = len(self.proactiveMessage[2:])

    def addDeviceIdentities(self, source, destination):
        """source, destination - use device_identity object"""
        self.addTagToMessage(comprehension_tag.DEVICE_IDENTITIES,
                        True, [source, destination])

    def addAlphaIdentifier(self, text, comprehensionRequired=True):
        self.addTagToMessage(comprehension_tag.ALPHA_IDENTIFIER, comprehensionRequired,
                             hextools.hex2bytes(text.encode("hex")))

    def addDuration(self, time_unit, time_interval):
        """Add duration tag
            time_unit:      use duration_time_unit object
            time_interval:  from 1 to 255 units
        """
        self.addTagToMessage(comprehension_tag.DURATION, True,
                             [time_unit, time_interval])

    def addItem(self, id, text):
        params = [id] + hextools.hex2bytes(text.encode("hex"))
        self.addTagToMessage(comprehension_tag.ITEM, True, params)

    def addItemIdentifier(self, id):
        params = [id]
        self.addTagToMessage(comprehension_tag.ITEM_IDENTIFIER, True, params)

    def addText(self, coding, text):
        """coding - use data_coding object"""
        params = [coding] + hextools.hex2bytes(text.encode("hex"))
        self.addTagToMessage(comprehension_tag.TEXT_STRING, True, params)

    def addResponseLength(self, minLength, maxLength):
        params = [minLength, maxLength]
        self.addTagToMessage(comprehension_tag.RESPONSE_LENGTH, True, params)

    def addTone(self, tone):
        params = [tone]
        self.addTagToMessage(comprehension_tag.TONE, True, params)

    def addFileList(self, list, comprehensionRequired=True):
        """Full paths should be given to files, e.g. IMSI: "3F007F206F07" """
        params = []
        # The number of files that will be described in the following list
        params.append(len(list))
        # Files - full paths are given to files
        for file in list:
            params.extend(hextools.hex2bytes(file))
        self.addTagToMessage(comprehension_tag.FILE_LIST, comprehensionRequired, params)

    def addIconIdentifier(self, iconID, qualifier):
        """
        iconID: record address in EFimg ('4F20') as defined in TS 131 102
        qualifier: 0 - replaces the alpha identifier or text string
                   1 -  it shall be displayed together with text string
        """
        params = [iconID, qualifier]
        self.addTagToMessage(comprehension_tag.ICON_IDENTIFIER, True, params)

    def addUSSDString(self, coding, string):
        """coding: use data_coding object"""
        params = [coding] + hextools.hex2bytes(string)
        self.addTagToMessage(comprehension_tag.USSD_STRING, True, params)

#############################
# Custom commands/functions
#############################
    def addItemList(self):
        items = self.SETUP_MENU_DICT["items"]
        #i = 0x80
        for key, item in items.items():
            # FIXME: iterates in the reverse direction
            self.addItem(int(key, 16), item['text'])

    def createSetupMenu(self):
        """command qualifier:
        bit 1: 0 = no selection preference;
               1 = selection using soft key preferred
        bits 2 to 7: = RFU.
        bit 8: 0 = no help information available;
               1 = help information available
        """
        self.buildProactiveMessage(cmd_type.SET_UP_MENU, 0x00)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_TERMINAL)
        text = self.SETUP_MENU_DICT["alpha"][0]
        self.addAlphaIdentifier(text)
        self.addItemList()
        # Items Next Action Indicator (optional)
        # Icon identifier (optional)
        # Item Icon identifier list (optional)
        # Text Attribute (optional)
        # Item Text Attribute List (optional)
        self.setMessagePending(True)

    def displayText(self, text, duration=None):
        """cmdQualifier:
        bit 1: 0 = normal priority; 1 = high priority.
        bit 8: 0 = clear message after a delay;
               1 = wait for user to clear message.
        """
        logging.info("displayText: " + text)
        if duration:
            cmdQualifier = 0x00
        else:
            cmdQualifier = 0x80
        self.buildProactiveMessage(cmd_type.DISPLAY_TEXT, cmdQualifier)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_DISPLAY)
        # Text string
        self.addText(data_coding.CODING_8_BIT_DATA, text)
        # Icon identifier (optional)
        # Immediate response (optional)
        # Duration (optional)
        if duration:
            self.addDuration(duration_time_unit.SECONDS, duration)
        # Text Attribute (optional)
        # Frame Identifier (optional)
        self.setMessagePending(True)

    def getInput(self, infoText, minLen, maxLen, cmdQualifier = 0x00):
        """cmdQualifier:
        bit 1: 0 = digits (0 to 9, *, #, and +) only; 1 = alphabet set.
        bit 2: 0 = SMS default alphabet; 1 = UCS2 alphabet.
        bit 3: 0 = terminal may echo user input on the display;
               1 = user input shall not be revealed in any way (see note).
        bit 4: 0 = user input to be in unpacked format;
               1 = user input to be in SMS packed format.
        bits 5 to 7: = RFU.
        bit 8: 0 = no help information available;
               1 = help information available.
        """
        self.buildProactiveMessage(cmd_type.GET_INPUT, cmdQualifier)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_TERMINAL)
        # Text string
        self.addText(data_coding.CODING_8_BIT_DATA, infoText)
        #FIXME: coding was 0xF4 in the example
        # check ETSI TS 123 038 V9.1.1 (section 4)
        # Response length
        self.addResponseLength(minLen, maxLen) # min:1, max:10 characters
        self.setMessagePending(True)
    """
    REFRESH
    The purpose of this command is to enable the terminal
    to be notified of the changes to the UICC configuration that have
    occurred as the result of a NAA application activity.
    NAA - Network Access Application
    """
    def refresh(self, mode, list=None):
        """mode: use refresh_mode object"""
        self.buildProactiveMessage(cmd_type.REFRESH, mode)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_TERMINAL)
        # File list (conditional - only for specific modes)
        if (mode == refresh_mode.SIM_INIT_AND_FILE_CHANGE_NOTIFICATION or
                mode == refresh_mode.FILE_CHANGE_NOTIFICATION or
                   mode == refresh_mode.USIM_RESET):
            if list != None:
                self.addFileList(list, comprehensionRequired=True) #False
            else:
                logging.info("Error! File List data object is not supplied.")
        # AID (optional - not for 2G platform)
        # Alpha identifier (optional)
        # Icon identifier (optional)
        # Text Attribute (conditional - may be present only if Alpha is present)
        # Frame identifier (optional)
        # Refresh enforcement policy (optional)
        self.setMessagePending(True)
    '''
    PROVIDE_LOCAL_INFO
    This command requests the terminal to send current local information
    to the UICC. The terminal shall return the requested local information
    within a TERMINAL RESPONSE.
    '''
    def provideLocalInformation(self, info):
        """info: use local_info object"""
        cmdQualifier = info # e.g. IMEI of the terminal
        self.buildProactiveMessage(cmd_type.PROVIDE_LOCAL_INFO, cmdQualifier)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_TERMINAL)
        self.setMessagePending(True)

    '''
    SELECT_ITEM
     Set of items from which the user may choose one.
    '''
    def selectItem(self, title, items):
        cmdQualifier = 0x00
        self.buildProactiveMessage(cmd_type.SELECT_ITEM, cmdQualifier)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_TERMINAL)
        # Alpha identifier (optional)
        if title:
            self.addAlphaIdentifier(title)
        # Item data objects
        for key, item in items.items():
            self.addItem(int(key, 16), item['text'])
        # Items Next Action Indicator (optional)
        # Item identifier (optional)
        # Icon identifier (optional)
        # Item Icon identifier list (optional)
        # Text Attribute (optional)
        # Item Text Attribute list (optional)
        # Frame identifier (optional)
        self.setMessagePending(True)

    def sendSMS(self):
        pass

    def setupCall(self):
        pass

    # Note: There is a generic problem with this command.
    #       After the tone is played the UICC session does not end.
    def playTone(self, tone, forceVibrate=False):
        """forceVibrate:
        bit 1: 0 = use of vibrate alert is up to the terminal;
               1 = vibrate alert, if available, with the tone.
        """
        self.buildProactiveMessage(cmd_type.PLAY_TONE, forceVibrate)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_TERMINAL)
        # Alpha identifier (optional)
        # Tone (optional)
        self.addTone(tone)
        # Duration (optional)
        self.addDuration(duration_time_unit.TENTHS_OF_SECONDS, 18) # 1.8 sec
        # Icon identifier (optional)
        # Text Attribute (optional)
        # Frame identifier (optional)
        self.setMessagePending(True)

    def lunchBrowser(self):
        pass

    def sendUSSD(self, string):
        cmdQualifier = 0 # this byte is RFU
        self.buildProactiveMessage(cmd_type.SEND_USSD, cmdQualifier)
        self.addDeviceIdentities(device_identity.DEV_UICC,
                                 device_identity.DEV_NETWORK)
        # Alpha identifier (optional)
        #self.addAlphaIdentifier("Sending USSD: " + string, comprehensionRequired=False)

        # USSD String
        # The MMI mode uses a 7 bit character set,
        # the Application mode uses a 8 bit character set
        #    coding = data_coding.CODING_MESSAGE_CLASS_0 | data_coding.CODING_8_BIT_DATA
        coding = data_coding.CODING_MESSAGE_CLASS_3 | data_coding.CODING_RESERVED
        self.addUSSDString(coding, string)
        # Icon identifier (optional)
        # Text Attribute (conditional)
        # Frame identifier (optional)
        self.setMessagePending(True)

    ################################################################

    # TODO: move elsewhere.
    # Example of direct soft SIM modification.
    def setSimPlmn(self, plmn):
        file = self.simXml.findFile("./mf/df[@id='7F20']/ef[@id='6F07']")
        imsi = self.simXml.getValue(file)
        _plmn = list(plmn) # e.g. '23012'
        _imsi = list(imsi) # e.g. '08 29 06 10 59 60 66 78 44'
        _imsi[3] = _plmn[0]
        _imsi[6] = _plmn[2]
        _imsi[7] = _plmn[1]
        _imsi[9] = _plmn[4]
        _imsi[10] = _plmn[3]

        # update IMSI with a new PLMN
        self.simXml.setValue(file, "".join((_imsi)))

    def addHandler(self, handlerArray, handler, data):
        dictHandler = {
            'handler' : handler,
            'data'    : data,
            }
        handlerArray.append(dictHandler)

    def assignResponseHandler(self, handler, handlerData=None):
        self.addHandler(self.responseHandler, handler, handlerData)

    def assignPostActionHandler(self, handler, handlerData=None):
        self.addHandler(self.postActionHandler, handler, handlerData)

    def statusOk(self, status, error=None):
        if not status:
            return True
        else:
            # TODO: check if every status information is caused by failure.
            if error:
                self.displayText(error)
            return False

    ### Menu Item 1 ###
    def onImeiGetCallback(self, status, imei, handlerData):
        if not self.statusOk(status, error="Failed to get imei"):
            return
        self.displayText(imei) # terminal IMEI

    def onImeiGet(self, data):
        # Send IMEI request
        self.provideLocalInformation(local_info.IMEI_OF_THE_TERMINAL)
        self.assignResponseHandler(self.onImeiGetCallback, data)

    ### Menu Item 2 ###
    def onPlmnSetCallback(self, status, plmn, simId):
        if not self.statusOk(status, error="Failed to change HPLMN!"):
            return
        # Get PLMN number and update IMSI
        if (plmn is None or len(plmn) not in [5,6] or
                all(char.isdigit() for char in plmn) == False):#check if all elements are numbers
            self.displayText("Wrong data format!")
            return
        if not self.simRouter:
            self.displayText("MIM not set!")
            return
        if not simId:
            simId = 0
        if simId >= self.simRouter.getNbrOfCards():
            self.displayText("simId: " + str(simId) + " not connected!")
            return
        self.displayText("Updating HPLMN, please wait...", duration=2)
        # TODO: add waiting dialog until postAction is finished.
        self.assignPostActionHandler(PostHandlerThread.postPlmnSet, [simId, plmn])

    def onPlmnSimIdGet(self, data):
        if self.simRouter and len(self.simRouter.cardsDict) > 1:
            # Get input of exactly 5 digits (PLMN)
            self.getInput("Enter SimId (e.g. 0)", 1, 1)
            self.assignResponseHandler(self.onPlmnSimIdGetCallback)
        else:
            # Only one card is connected.
            self.onPlmnSet(status=None, simId=0)

    def onPlmnSimIdGetCallback(self, status, simId, handlerData):
        if not self.statusOk(status):
            return
        if simId.isdigit():
            simId = int(simId)
        else:
            self.displayText("Wrong format, digit expected!")
            return
        self.onPlmnSet(status, simId)

    def onPlmnSet(self, status, simId):
        if not self.statusOk(status):
            return
        # Get input of exactly 5 digits (PLMN)
        self.getInput("Enter HPLMN (e.g. 00101)", 5, 5)
        self.assignResponseHandler(self.onPlmnSetCallback, simId)

    ### Menu Item 3 ###
    def onMelodyPlay(self, data):
        """Play Tone"""
        self.playTone(2) # '02' Called subscriber busy
        self.assignResponseHandler(self.onMelodyPlayCallback)

    def onMelodyPlayCallback(self, status, respData, handlerData):
        if not self.statusOk(status):
            return
        # Added displayText() as workaround to not stuck in setup menu.
        self.displayText("Finished playing tone ", duration=1)

    ### Menu Item 4 ###
    def onSimSwap(self, data):
        if not self.simRouter or len(self.simRouter.cardsDict) < 2:
            # One card is connected, go directly to refresh menu.
            self.onSimRefresh(data=None)
            return
        self.selectItem("Swap SIM cards", self.SWAP_SIMS)
        self.assignResponseHandler(self.onSimSwapCallback)

    def onSimSwapCallback(self, status, mode, handlerData):
        if not self.statusOk(status):
            return
        if mode == 0:  # 0x80
            self.simRouter.swapCards(simId1=0, simId2=1)
        self.onSimRefresh(data=None)

    ### Menu Item 4 ###
    def onSimRefresh(self, data):
        self.selectItem("Refresh mode", self.REFRESH_SIM_ITEMS)
        self.assignResponseHandler(self.onSimRefreshCallback)

    def onSimRefreshCallback(self, status, mode, handlerData):
        if not self.statusOk(status):
            return
        logging.error("Refresh mode: " + str(mode))
        if mode == 0: #0x80
            self.refresh(refresh_mode.SIM_INIT_AND_FULL_FILE_CHANGE_NOTIFICATION)
        elif mode == 1: #0x81
            self.refresh(refresh_mode.SIM_RESET)
        elif mode == 2: #0x82
            self.refresh(refresh_mode.SIM_INIT_AND_FILE_CHANGE_NOTIFICATION, [
                "3F007F106F42",
                "3F007F206F74",
                "3F007FFF6F07",
                "3F007FFF6F73",
                "3F007FFF6F7B",
                "3F007FFF6F7E",
                "3F007FFF6F42",
                "3F007FFF5F3B4F20",
                "3F007FFF5F3B4F52"])
        else:
            self.displayText("Unsupported refresh mode")

    ### Menu Item 5 ###
    def onUssdSend(self, data):
        self.getInput("Enter USSD (e.g. *100#)", 3, 20)
        self.assignResponseHandler(self.onUssdSendCallback)

    def onUssdSendCallback(self, status, ussd, handlerData):
        if not self.statusOk(status):
            return
        ussdData = coder.encodeGsm7(ussd)
        #ussdData = "".join("{:02x}".format(ord(c)) for c in ussd)
        self.sendUSSD(ussdData)
        self.assignResponseHandler(self.onUssdSendCallback2)

    def onUssdSendCallback2(self, status, respData, handlerData):
        if status and 'result' in status.keys():
            error = general_result[status['result']]
        else:
            error = None
        if not self.statusOk(status, error) or not respData:
            return
        dcs = respData.pop(0) # dcs - Data Coding Style
        text = coder.decodeGsm7(hextools.bytes2hex(respData))
        #response = data
        self.displayText(text)

    ### Menu Item 6 ###
    def onCardsList(self, data):
        # TODO: try to omit provideLocalInformation to trigger postActionHandler.
        self.provideLocalInformation(local_info.LANGUAGE)
        self.assignResponseHandler(self.onCardsListCallback, data)

    def onCardsListCallback(self, status, lan, handlerData):
        # TODO: try to omit displayText to trigger postActionHandler.
        self.displayText("Reading cards, please wait...", duration=4)
        self.assignPostActionHandler(PostHandlerThread.postCardsList)

    def satShell(self, param, value):
        param = param.lower()
        if param == "refresh":
            self.onSimRefreshCallback(status=None, mode=int(value), handlerData=None)
        elif param == "list_cards":
            self.onCardsListCallback(status=None, lan=None, handlerData=None)
            self.runPostActionHandler(status=None, respData=0)
        else:
            logging.error("Unsupported param: " + param)
            return False
        return True

    SETUP_MENU_ALPHA = ["simLAB"]

    # Note: below dict needs to be defined below handler functions
    # FIXME: item numbers '80' -> '00'
    SETUP_MENU_ITEMS = {
        '80':{'text': "Read IMEI",            'handler': onImeiGet},
        '81':{'text': "Change HPLMN",         'handler': onPlmnSimIdGet},
        '82':{'text': "Play Tone",            'handler': onMelodyPlay},
        '83':{'text': "Refresh SIM",          'handler': onSimSwap},
        '84':{'text': "Send USSD",            'handler': onUssdSend},
        '85':{'text': "List SIM cards",       'handler': onCardsList},
        }

    SETUP_MENU_DICT = {
        "alpha" : SETUP_MENU_ALPHA,
        "items" : SETUP_MENU_ITEMS
        }

    REFRESH_SIM_ITEMS = {
        '80':{'text': "SIM init and full file notification"},
        '81':{'text': "SIM reset"},
        '82':{'text': "SIM init and file list notification"},
        }

    SWAP_SIMS = {
        '80':{'text': "Swap SIM cards"},
        '81':{'text': "Don't swap SIM cards"},
        }

class PostHandlerThread(threading.Thread):
    def __init__(self, satCtrl, handler, status, respData, data):
        threading.Thread.__init__(self)
        self.satCtrl = satCtrl
        self.handler = handler
        self.status = status
        self.respData = respData
        self.data = data
        self.currentSimId = self.satCtrl.simRouter.simCtrl.srvId
        threading.Thread.setName(self, 'PostHandlerThread')
        self.__lock = threading.Lock()

    def startThread(self):
        threading.Thread.start(self)

    def run(self):
        self.__lock.acquire()
        from sim import sim_shell
        self.shell = self.satCtrl.simRouter.shell
        self.handler(self, self.status, self.respData, self.data)
        self.__lock.release()

    def stop(self):
        # Restore simId.
        self.satCtrl.simRouter.simCtrl.setSrvCtrlId(self.currentSimId)

    def postPlmnSet(self, status, respData, data):
        if not self.satCtrl.statusOk(status):
            return
        simId = data[0]
        plmn = data[1]
        self.satCtrl.simRouter.simCtrl.setSrvCtrlId(simId)

        status, data = self.shell.set_plmn(plmn)
        if not self.shell.statusOk(status):
            self.satCtrl.displayText("HPLMN change failed!")
            self.satCtrl.stopPostActionHandler()
            return
        self.satCtrl.displayText("HPLMN updated", duration=1)
        self.satCtrl.stopPostActionHandler()

    def postCardsList(self, status, respData, data):
        if not self.satCtrl.statusOk(status):
            return
        text = ""
        for simId, cardDict in enumerate(self.satCtrl.simRouter.cardsDict):
            self.satCtrl.simRouter.simCtrl.setSrvCtrlId(simId)
            status, data = self.shell.readi("EF_IMSI")
            if not self.shell.statusOk(status):
                self.satCtrl.displayText("IMSI read failed!")
                self.satCtrl.stopPostActionHandler()
                return
            imsi = types.getDataValue(data)
            imsiReadByPhone = cardDict[0].imsi
            if imsiReadByPhone == imsi:
                readByPhone = "*"
            elif imsiReadByPhone != None:
                readByPhone = "#"
            else:
                readByPhone = ""
            text += ("SIM id: " + str(simId) + "\n" +
                    "  IMSI: " + imsi + " " + readByPhone + "\n")
        self.satCtrl.displayText("Cards connected\n" + text)
        self.satCtrl.stopPostActionHandler()