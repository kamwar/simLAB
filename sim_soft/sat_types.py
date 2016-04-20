# LICENSE: GPL2
# (c) 2014 Szymon Mielczarek

# Fixed lengths of some COMPREHENSION-TLV data objects
TLV_COMMAND_DETAILS_LENGTH = 0x03
TLV_DEVICE_IDENTITIES_LENGTH = 0x02
TLV_DURATION_LENGTH = 0x02
TLV_ITEM_IDENTIFIER_LENGTH = 0x01
TLV_RESPONSE_LENGTH = 0x02

class data_coding(object):
    #SMS class
    CODING_MESSAGE_CLASS_0 = 0b00000000
    CODING_MESSAGE_CLASS_1 = 0b00000001
    CODING_MESSAGE_CLASS_2 = 0b00000010
    CODING_MESSAGE_CLASS_3 = 0b00000011

    #character set
    CODING_GSM7            = 0b00000000
    CODING_8_BIT_DATA      = 0b00000100
    CODING_UCS2            = 0b00001000
    CODING_RESERVED        = 0b00001100

class gsm_charset(object):
    CHARSET_UTF8 = 1
    CHARSET_UCS2 = 2
    CHARSET_GSM = 3

class duration_time_unit(object):
    MINUTES = 0x00
    SECONDS = 0x01
    TENTHS_OF_SECONDS = 0x02

# REFRESH modes (command qualifiers)
class refresh_mode(object):
    # NAA Initialization and Full File Change Notification
    SIM_INIT_AND_FULL_FILE_CHANGE_NOTIFICATION = 0x00
    # File Change Notification
    FILE_CHANGE_NOTIFICATION                   = 0x01
    # NAA Initialization and File Change Notification
    SIM_INIT_AND_FILE_CHANGE_NOTIFICATION      = 0x02
    # NAA Initialization
    SIM_INIT                                   = 0x03
    # UICC Reset
    SIM_RESET                                  = 0x04
    # NAA Application Reset, only applicable for a 3G platform
    USIM_INIT                                  = 0x05
    # NAA Session Reset, only applicable for a 3G platform
    USIM_RESET                                 = 0x06

# LOCAL INFORMATION (command qualifiers)
class local_info(object):
    # Location Information according to current NAA
    LOCATION_INFO_PER_NAA                       = 0x00
    # IMEI of the terminal
    IMEI_OF_THE_TERMINAL                        = 0x01
    # Network Measurement results according to current NAA
    NETWORK_MEASUREMENT_RESULTS_PER_NAA         = 0x02
    # Date, time and time zone
    DATETIME                                    = 0x03
    # Language setting
    LANGUAGE                                    = 0x04
    # Reserved for GSM
    RESERVED_FOR_GSM                            = 0x05
    # Access Technology (single access technology)
    ACCESS_TECHNOLOGY                           = 0x06
    # ESN of the terminal
    ESN_OF_THE_TERMINAL                         = 0x07
    # IMEISV of the terminal
    IMEISV_OF_THE_TERMINAL                      = 0x08
    # Search Mode
    SEARCH_MODE                                 = 0x09
    # Charge State of the Battery (if class "g" is supported)
    BATTERY_CHARGE_STATE                        = 0x0A
    # MEID of the terminal
    MEID_OF_THE_TERMINAL                        = 0x0B
    # reserved for 3GPP (current WSID)
    RESERVED_FOR_3GPP                           = 0x0C
    # Broadcast Network information
    # according to current Broadcast Network Technology used
    BROADCAST_NETWORK_INFO                      = 0x0D
    # Multiple Access Technologies
    MULTIPLE_ACCESS_TECHNOLOGY                  = 0x0E
    # Location Information for multiple access technologies
    LOCATION_INFO_FOR_MULTITECH                 = 0x0F
    # Network Measurement results for multiple access technologies
    NETWORK_MEASUREMENT_RESULTS_FOR_MULTITECH   = 0x10
    # '11' to 'FF' = Reserved.

# Tag values used to identify the BER-TLV and COMPREHENSION-TLV data objects
# TS 102.223 v12.1.0 (sections 9.1-9.3)
# TS 101 220 V8.4.0 (page 14)
# BER (Basing encoding rules)
class ber_tag(object):
    PROACTIVE = 0xD0
    SMS_PP_DOWNLOAD = 0xD1
    CELL_BROADCAST_DOWNLOAD = 0xD2
    MENU_SELECTION = 0xD3
    CALL_CONTROL = 0xD4
    MO_SHORT_MSG_CONTROL = 0xD5 # GSM/3G
    EVENT_DOWNLOAD = 0xD6
    TIMER_EXPIRATION = 0xD7
    USSD_DOWNLOAD = 0xD9 # 3G
    MMS_TRANSFER_STATUS = 0xDA
    MMS_NOTIFICATION_DOWNLOAD = 0xDB
    TERMINAL_APPLICATION = 0xDC
    # and some more

class comprehension_tag(object):
    COMPREHENSION_REQUIRED = 0x80
    COMMAND_DETAILS = 0x01
    DEVICE_IDENTITIES = 0x02
    RESULT = 0x03
    DURATION = 0x04
    ALPHA_IDENTIFIER = 0x05
    ADDRESS = 0x06
    CAPABILITY_CONFIGURATION_PARAMETERS = 0x07
    CALLED_PARTY_SUBADDRESS = 0x08
    SS_STRING = 0x09 # Reserved for GSM/3G
    USSD_STRING = 0x0A # Reserved for GSM/3G
    SMS_TPDU = 0x0B # Reserved for GSM/3G
    CELL_BROADCAST_PAGE = 0x0C # Reserved for GSM/3G
    TEXT_STRING = 0x0D
    TONE = 0x0E
    ECAT_CLIENT_PROFILE = 0x0E
    ITEM = 0x0F
    ECAT_CLIENT_IDENTITY = 0x0F
    ITEM_IDENTIFIER = 0x10
    ENCAPSULATED_ENVELOPE = 0x10
    RESPONSE_LENGTH = 0x11
    FILE_LIST = 0x12
    LOCATION_INFORMATION = 0x13
    IMEI = 0x14
    HELP_REQUEST = 0x15
    ICON_IDENTIFIER = 0x1E
    # and many more (up to 0x7B)

# TS 102.223 v12.1.0 (section 9.4)
class cmd_type(object):
    REFRESH = 0x01
    MORE_TIME = 0x02
    POLL_INTERVAL = 0x03
    POLLING_OFF = 0x04
    SETUP_EVENT_LIST = 0x05
    SET_UP_CALL = 0x10
    SEND_SS = 0x11
    SEND_USSD = 0x12
    SEND_SHORT_MESSAGE = 0x13
    SEND_DTMF = 0x14
    LAUNCH_BROWSER = 0x15
    GEOGRAPHICAL_LOCATION_REQUEST = 0x16
    PLAY_TONE = 0x20
    DISPLAY_TEXT = 0x21
    GET_INKEY = 0x22
    GET_INPUT = 0x23
    SELECT_ITEM = 0x24
    SET_UP_MENU = 0x25
    PROVIDE_LOCAL_INFO = 0x26
    TIMER_MANAGEMENT = 0x27
    SETUP_IDLE_MODE_TEXT = 0x28
    CARD_APDU = 0x30
    POWER_ON_CARD = 0x31
    POWER_OFF_CARD = 0x32
    GET_READER_STATUS = 0x33
    RUN_AT_COMMAND = 0x34
    LANG_NOTIFICATION = 0x35
    OPEN_CHANNEL = 0x40
    CLOSE_CHANNEL = 0x41
    RECEIVE_DATA = 0x42
    SEND_DATA = 0x43
    GET_CHANNEL_STATUS = 0x44
    SERVICE_SEARCH = 0x45
    GET_SERVICE_INFORMATION = 0x46
    DECLARE_SERVICE = 0x47
    SET_FRAMES = 0x50
    GET_FRAMES_STATUS = 0x51
    RETRIEVE_MM = 0x60
    SUBMIT_MM = 0x61
    DISPLAY_MM = 0x62
    ACTIVATE = 0x70
    CONTACTLESS_STATE_CHANGED = 0x71
    COMMAND_CONTAINER = 0x72
    ENCAPSULATED_SESSION_CONTROL = 0x73
    END_OF_PROACTIVE_SESSION = 0x81

# TS 102.223 v12.1.0 (section 8.7)
class device_identity(object):
    DEV_KEYPAD = 0x01
    DEV_DISPLAY = 0x02
    DEV_EARPIECE = 0x03
    DEV_ADDT_CARD_READER = 0x10
    # card reader id (0 to 7)
    DEV_CHANNEL_IDENTIFIER = 0x20
    # channel id (1 to 7)
    DEV_ECAT_CLIENT_IDENTIFIER = 0x30
    # client id (1 to 15)
    DEV_UICC = 0x81
    DEV_TERMINAL = 0x82
    DEV_NETWORK = 0x83

# 8.12 Result: General result
general_result = {
    0x00 : 'Command performed successfully',
    0x01 : 'Command performed with partial comprehension',
    0x02 : 'Command performed, with missing information',
    0x03 : 'REFRESH performed with additional Efs read',
    0x04 : 'Command performed successfully, but requested icon could not be displayed',
    0x05 : 'Command performed, but modified by call control by NAA',
    0x06 : 'Command performed successfully, limited service',
    0x07 : 'Command performed with modification; ETSI',
    # Release 12 151 ETSI TS 102 223 V12.1.0 (2014-09)
    0x08 : 'REFRESH performed but indicated NAA was not active',
    0x09 : 'Command performed successfully, tone not played',
    0x10 : 'Proactive UICC session terminated by the user',
    0x11 : 'Backward move in the proactive UICC session requested by the user',
    0x12 : 'No response from user',
    0x13 : 'Help information required by the user',
    0x14 : 'USSD or SS transaction terminated by the user',
    # Results '0X' and '1X' indicate that the command has been performed:
    0x20 : 'terminal currently unable to process command',
    0x21 : 'Network currently unable to process command',
    0x22 : 'User did not accept the proactive command',
    0x23 : 'User cleared down call before connection or network release',
    0x24 : 'Action in contradiction with the current timer state',
    0x25 : 'Interaction with call control by NAA, temporary problem',
    0x26 : 'Launch browser generic error code',
    0x27 : 'MMS temporary problem',
    # Results '2X' indicate to the UICC that
    # it may be worth re-trying the command at a later opportunity:
    0x30 : 'Command beyond terminal\'s capabilities',
    0x31 : 'Command type not understood by terminal',
    0x32 : 'Command data not understood by terminal',
    0x33 : 'Command number not known by terminal',
    0x34 : 'SS Return Error',
    0x35 : 'SMS RP-ERROR',
    0x36 : 'Error, required values are missing',
    0x37 : 'USSD Return Error',
    0x38 : 'MultipleCard commands error',
    0x39 : 'Interaction with call control by NAA, permanent problem',
    0x3A : 'Bearer Independent Protocol error',
    0x3B : 'Access Technology unable to process command',
    0x3C : 'Frames error',
    0x3D : 'MMS Error',
    # Results '3X' indicate that it is not worth
    # the UICC re-trying with an identical command, as it will only get the
    #same response. However, the decision to retry lies with the application.
}
