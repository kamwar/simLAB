# LICENSE: GPL2
# (c) 2012 Kevin Redon <kevredon@mail.tsaitgaist.info>
# (c) 2013 Tom Schouten <tom@getbeep.com>

# how to decode the terminal profile
# from ETSI TS 102 223 V11.0.0  - 5.2
# Table Pythonified by Tom from from https://terminal-profile.osmocom.org/terminal_profile.rb
template = [
  ( "Download", [
    (1,  "Profile download"),
    (1,  "3GPP: SMS-PP data download"),
    (1,  "3GPP: Cell Broadcast data download"),
    (1,  "Menu selection"),
    (1,  "3GPP: SMS-PP data download"),
    (1,  "Timer expiration"),
    (1,  "3GPP: USSD string data object support in Call Control by USIM"),
    (1,  "Call Control by NAA")
  ]),
  ( "Other", [
    (1,  "Command result"),
    (1,  "Call Control by NAA"),
    (1,  "Call Control by NAA"),
    (1,  "MO short message control support"),
    (1,  "Call Control by NAA"),
    (1,  "UCS2 Entry supported"),
    (1,  "UCS2 Display supported"),
    (1,  "Display Text")
  ]),
  ( "Proactive UICC", [
    (1,  "DISPLAY TEXT"),
    (1,  "GET INKEY"),
    (1,  "GET INPUT"),
    (1,  "MORE TIME"),
    (1,  "PLAY TONE"),
    (1,  "POLL INTERVAL"),
    (1,  "POLLING OFF"),
    (1,  "REFRESH")
  ]),
  ( "Proactive UICC", [
    (1,  "SELECT ITEM"),
    (1,  "3GPP: SEND SHORT MESSAGE with 3GPP-SMS-TPDU"),
    (1,  "3GPP: SEND SS"),
    (1,  "3GPP: SEND USSD"),
    (1,  "SET UP CALL"),
    (1,  "SET UP MENU"),
    (1,  "PROVIDE LOCAL INFORMATION (MCC, MNC, LAC, Cell ID & IMEI)"),
    (1,  "PROVIDE LOCAL INFORMATION (NMR)")
  ]),
  ( "Event driven information", [
    (1,  "Proactive UICC: SET UP EVENT LIST"),
    (1,  "MT call"),
    (1,  "Call connected"),
    (1,  "Call disconnected"),
    (1,  "Location status"),
    (1,  "User activity"),
    (1,  "Idle screen available"),
    (1,  "Card reader status")
  ]),
  ( "Event driven information extensions (for class a)", [
    (1,  "Language selection"),
    (1,  "Browser Termination"),
    (1,  "Data available"),
    (1,  "Channel status"),
    (1,  "Access Technology Change"),
    (1,  "Display parameters changed"),
    (1,  "Local Connection"),
    (1,  "Network Search Mode Change")
  ]),
  ( "Multiple card proactive commands (for class a) (Proactive UICC)", [
    (1,  "POWER ON CARD"),
    (1,  "POWER OFF CARD"),
    (1,  "PERFORM CARD APDU"),
    (1,  "GET READER STATUS (Card reader status)"),
    (1,  "GET READER STATUS (Card reader identifier)")
  ]),
  ( "Proactive UICC", [
    (1,  "TIMER MANAGEMENT (start, stop)"),
    (1,  "TIMER MANAGEMENT (get current value)"),
    (1,  "PROVIDE LOCAL INFORMATION (date, time and time zone)"),
    (1,  "GET INKEY"),
    (1,  "SET UP IDLE MODE TEXT"),
    (1,  "RUN AT COMMAND"),
    (1,  "SETUP CALL"),
    (1,  "Call Control by NAA")
  ]),
  ( "Proactive UICC", [
    (1,  "DISPLAY TEXT"),
    (1,  "SEND DTMF command"),
    (1,  "PROVIDE LOCAL INFORMATION (NMR)"),
    (1,  "PROVIDE LOCAL INFORMATION (language)"),
    (1,  "3GPP: PROVIDE LOCAL INFORMATION, Timing Advance"),
    (1,  "LANGUAGE NOTIFICATION"),
    (1,  "LAUNCH BROWSER"),
    (1,  "PROVIDE LOCAL INFORMATION (Access Technology)")
  ]),
  ( "Soft keys support (for class d)", [
    (1,  "Soft keys support for SELECT ITEM"),
    (1,  "Soft keys support for SET UP MENU")
  ]),
  ( "Soft keys information", [
    (8,  "Maximum number of soft keys available")
  ]),
  ( "Bearer Independent protocol proactive commands (for class e) (Proactive UICC)", [
    (1,  "OPEN CHANNEL"),
    (1,  "CLOSE CHANNEL"),
    (1,  "RECEIVE DATA"),
    (1,  "SEND DATA"),
    (1,  "GET CHANNEL STATUS"),
    (1,  "SERVICE SEARCH"),
    (1,  "GET SERVICE INFORMATION"),
    (1,  "DECLARE SERVICE")
  ]),
  ( "Bearer Independent protocol proactive commands (for class e)", [
    (1,  "CSD"),
    (1,  "GPRS"),
    (1,  "Bluetooth"),
    (1,  "IrDA"),
    (1,  "RS232"),
    (3,  "Number of channels supported by terminal")
  ]),
  ( "Screen height", [
    (5,  "Number of characters supported down the terminal display"),
    (1,  "No display capability"),
    (1,  "No keypad available"),
    (1,  "Screen Sizing Parameters supported")
  ]),
  ( "Screen width", [
    (7,  "Number of characters supported across the terminal display"),
    (1,  "Variable size fonts")
  ]),
  ( "Screen effects", [
    (1,  "Display can be resized"),
    (1,  "Text Wrapping supported"),
    (1,  "Text Scrolling supported"),
    (1,  "Text Attributes supported"),
    (1,  "RFU"),
    (3,  "Width reduction when in a menu")
  ]),
  ( "Bearer independent protocol supported transport interface/bearers (for class e)", [
    (1,  "TCP, UICC in client mode, remote connection"),
    (1,  "UDP, UICC in client mode, remote connection"),
    (1,  "TCP, UICC in server mode"),
    (1,  "TCP, UICC in client mode, local connection (i.e. class k is supported)"),
    (1,  "UDP, UICC in client mode, local connection (i.e. class k is supported)"),
    (1,  "Direct communication channel (i.e. class k is supported)"),
    (1,  "3GPP: E-UTRAN"),
    (1,  "3GPP: HSDPA")
  ]),
  ( "Proactive UICC", [
    (1,  "DISPLAY TEXT (Variable Time out)"),
    (1,  "GET INKEY (help is supported while waiting for immediate response or variable timeout)"),
    (1,  "USB (Bearer Independent protocol supported bearers, class e)"),
    (1,  "GET INKEY (Variable Timeout)"),
    (1,  "PROVIDE LOCAL INFORMATION (ESN)"),
    (1,  "Call control on GPRS"),
    (1,  "PROVIDE LOCAL INFORMATION (IMEISV)"),
    (1,  "PROVIDE LOCAL INFORMATION (Search Mode change)")
  ]),
  ( "reserved for TIA/EIA-136-C facilities", [
    (4,  "Protocol Version support")
  ]),
  ( "reserved for TIA/EIA/IS-820-A facilities", [] ),
  ( "Extended Launch Browser Capability (for class c)", [
    (1,  "WML"),
    (1,  "XHTML"),
    (1,  "HTML"),
    (1,  "CHTML")
  ]),
  ( "", [
    (1,  "3GPP: Support of UTRAN PS with extended parameters"),
    (1,  "Proactive UICC: PROVIDE LOCAL INFORMATION (battery state), (i.e. class g is supported)"),
    (1,  "Proactive UICC: PLAY TONE (Melody tones and Themed tones supported)"),
    (1,  "Multi-media Calls in SET UP CALL (if class h supported)"),
    (1,  "3GPP: Toolkit-initiated GBA"),
    (1,  "Proactive UICC: RETRIEVE MULTIMEDIA MESSAGE (if class j is supported)"),
    (1,  "Proactive UICC: SUBMIT MULTIMEDIA MESSAGE (if class j is supported)"),
    (1,  "Proactive UICC: DISPLAY MULTIMEDIA MESSAGE (if class j is supported)")
  ]),
  ( "", [
    (1,  "Proactive UICC: SET FRAMES (i.e. class i is supported)"),
    (1,  "Proactive UICC: GET FRAMES STATUS (i.e. class i is supported)"),
    (1,  "MMS notification download (if class j is supported)"),
    (1,  "Alpha Identifier in REFRESH command supported by terminal"),
    (1,  "3GPP: Geographical Location Reporting (if class n is supported)"),
    (1,  "Proactive UICC: PROVIDE LOCAL INFORMATION (MEID)"),
    (1,  "Proactive UICC: PROVIDE LOCAL INFORMATION (NMR(UTRAN/E-UTRAN))"),
    (1,  "3GPP: USSD Data download and application mode")
  ]),
  ( "(for class i)", [
    (4,  "Maximum number of frames supported (including frames created in existing frames)")
  ]),
  ( "Event driven information extensions", [
    (1,  "Event: Browsing status"),
    (1,  "Event: MMS Transfer status (if class j is supported)"),
    (1,  "Event: Frame Information changed (i.e. class i is supported)"),
    (1,  "3GPP: Event: I-WLAN Access status (if class e is supported)"),
    (1,  "3GPP: Event Network Rejection"),
    (1,  "Event: HCI connectivity event (i.e. class m is supported)"),
    (1,  "3GPP: E-UTRAN support in Event Network Rejection)"),
    (1,  "Multiple access technologies supported in Event Access Technology Change and PROVIDE LOCAL INFORMATION")
  ]),
  ( "Event driven information extensions", [
    (1,  "Event : CSG Cell Selection (if class q is supported"),
    (1,  "Event: Contactless state request (if class r is supported)"),
    (1,  "Multiple access technologies supported in Event Access Technology Change and PROVIDE LOCAL INFORMATION")
  ]),
  ( "Event driven information extensions", [] ),
  ( "Text attributes", [
    (1,  "Alignment left supported by Terminal"),
    (1,  "Alignment centre supported by Terminal"),
    (1,  "Alignment right supported by Terminal"),
    (1,  "Font size normal supported by Terminal"),
    (1,  "Font size large supported by Terminal"),
    (1,  "Font size small supported by Terminal")
  ]),
  ( "Text attributes", [
    (1,  "Style normal supported by Terminal"),
    (1,  "Style bold supported by Terminal"),
    (1,  "Style italic supported by Terminal"),
    (1,  "Style underlined supported by Terminal"),
    (1,  "Style strikethrough supported by Terminal"),
    (1,  "Style text foreground colour supported by Terminal"),
    (1,  "Style text background colour supported by Terminal")
  ]),
  ( "", [
    (1,  "3GPP: I-WLAN bearer support (if class e is supported)"),
    (1,  "3GPP: Proactive UICC: PROVIDE LOCAL INFORMATION (WSID of the current I-WLAN connection)"),
    (1,  "TERMINAL APPLICATIONS (i.e. class k is supported)"),
    (1,  "3GPP: Steering of Roaming REFRESH support"),
    (1,  "Proactive UICC: ACTIVATE (i.e. class l is supported)"),
    (1,  "3GPP: Proactive UICC: GEOGRAPHICAL LOCATION REQUEST (if class n is supported)"),
    (1,  "Proactive UICC: PROVIDE LOCAL INFORMATION (Broadcast Network Information) (i.e. class o is supported)"),
    (1,  "3GPP: Steering of Roaming for I-WLAN REFRESH support")
  ]),
  ( "", [
    (1,  "Proactive UICC: Contactless State Changed (if class r is supported)"),
    (1,  "3GPP: Support of CSG cell discovery (if class q is supported)"),
    (1,  "Confirmation parameters supported for OPEN CHANNEL in Terminal Server Mode"),
    (1,  "3GPP: Communication Control for IMS"),
    (1,  "Support of CAT over the modem interface (if class s is supported)"),
    (1,  "3GPP Support for Incoming IMS Data event (if classes e and t are supported)"),
    (1,  "3GPP Support for IMS Registration event (if classes e and t are supported)"),
    (1,  "Proactive UICC: Profile Container, Envelope Container, COMMAND CONTAINER and ENCAPSULATED SESSION CONTROL (if class u is supported)")
  ]),
  ( "", [
    (1,  "3GPP: Support of IMS as a bearer for BIP (if classes e and t are supported)")
  ])
]


def parse(bytes):
    for (title, fields), byte in zip(template, bytes):
        print title
        for nb_bits,name in fields:
            f = byte & nb_bits
            logging.info(" %d %s" % (f, name))
            byte = byte >> nb_bits




def test():
    from util import hextools
    parse(hextools.bytes("FFFFFFFF1F0000DFD7030A000000000600000000")) # N1

if __name__ == '__main__':
    test()
