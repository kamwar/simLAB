# LICENSE: GPL2
# (c) 2013 Tom Schouten <tom@getbeep.com>
# (c) 2014 Kamil Wartanowicz

# Central place to store all symbolic<->numeric tag conversions.

# Build bi-directional lookup with some automatic conversion

# Sentinel
class empty_table:
    def __getattr__(self, key):
        raise Exception("symbolic key not found: 0x%02X" % key)
    def __getitem__(self, key):
        raise Exception("numeric key not found: 0x%02X" % key)

class sym_table:
    def __init__(self, num_to_sym, parent = empty_table()):
        self.parent = parent
        self.n2s = num_to_sym
        self.s2n = dict([(s,n) for n,s in num_to_sym.items()])
    # table.key
    def __getattr__(self, key):
        try:
            return self.s2n[key]
        except:
            return self.parent.__getattr__(key)
    # table[key]
    def __getitem__(self, key):
        try:
            return self.n2s[key]
        except:
            return self.parent.__getitem__(key)

# ETSI TS 102 221 - 10.2.1 Status conditions returned by the UICC
sw1 = sym_table({
    0x61 : 'RESPONSE_DATA_AVAILABLE_3G',
    0x63 : 'CODE_ATTEMPTS_LEFT',
    0x67 : 'INCORRECT_PARAMETER_P3',
    0x6C : 'REPEAT_COMMAND_WITH_LE',
    0x6D : 'UNKNOWN_INSTRUCTION_CODE',
    0x6E : 'WRONG_INSTRUCTION_CLASS',
    0x6F : 'TECHNICAL_PROBLEM',
    0x91 : 'NO_ERROR_PROACTIVE_DATA',
    0x92 : 'NO_ERROR_DATA_TRANSFER',
    0x9F : 'RESPONSE_DATA_AVAILABLE_2G',
})

sw = sym_table({
    0x9000 : 'NO_ERROR',
    0x9300 : 'TOOLKIT_BUSY',
    # Warnings (state of non-volatile memory unchanged).
    0x6200 : 'WARNING_CARD_STATE_UNCHANGED', # (No information given)
    0x6282 : 'END_OF_FILE_REACHED',
    0x6283 : 'SELECTED_FILE_INVALIDATED',
    0x6285 : 'SELECTED_FILE_TERMINATED',
    0x62F1 : 'MORE_DATA_AVAILABLE',
    0x62F2 : 'MORE_DATA_AVAILABLE_AND_PROACTIVE_COMMAND_PENDING',
    0x62F3 : 'RESPONSE_DATA_AVAILABLE',
    # Warnings (state of non-volatile memory changed).
    0x63F1 : 'MORE_DATA_EXPECTED',
    0x63F2 : 'MORE_DATA_EXPECTED_AND_PROACTIVE_COMMAND_PENDING',
    0x63CF : 'VERIFICATION_FAILED',
    # Execution errors (state of non-volatile memory unchanged).
    0x6400 : 'ERROR_CARD_STATE_UNCHANGED', # (No information given)
    # Execution errors (state of non-volatile memory changed).
    0x6500 : 'ERROR_CARD_STATE_CHANGED', # (No information given)
    0x6581 : 'MEMORY_PROBLEM',
    # Checking errors.
    0x6700 : 'WRONG_LENGTH',
    # Functions in CLA not supported.
    0x6800 : 'FUNCTION_IN_CLA_NOT_SUPPORTED', # (No information given)
    0x6881 : 'LOGICAL_CHANNEL_NOT_SUPPORTED',
    0x6882 : 'SECURE_MESSAGING_NOT_SUPPORTED',
    # Command not allowed.
    0x6900 : 'COMMAND_NOT_ALLOWED', # (No information given)
    0x6981 : 'COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE',
    0x6982 : 'SECURITY_STATUS_NOT_SATISFIED',
    0x6983 : 'AUTHENTICATION_METHOD_BLOCKED',
    0x6984 : 'REFERNCE_DATA_INVALIDATE',
    0x6985 : 'CONDITIONS_OF_USE_NOT_SATISFIED',
    0x6986 : 'COMMAND_NOT_ALLOWED_NO_EF_SELECTED',
    0x6989 : 'COMMAND_NOT_ALLOWED_SECURE_CHANNEL_SECURITY_NOT_SATISFIED',
    0x6999 : 'APPLET_SELECT_FAILED',
    # Wrong parameter(s) P1-P2.
    0x6A80 : 'INCORRECT_PARAMETER_IN_DATA_FIELD',
    0x6A81 : 'INVALID_INSTRUCTION',
    0x6A82 : 'FILE_NOT_FOUND',
    0x6A83 : 'INVALID_DATA_ADDRESS',
    0x6A84 : 'NOT_ENOUGH_MEMORY_SPACE',
    0x6A86 : 'INCORRECT_PARAMETERS_P1_P2', # for SFI mode (out of range)
    0x6A87 : 'INCORRECT_PARAMETER_P3', # Lc
    0x6A88 : 'REFERENCE_DATA_NOT_FOUND',
    0x6A89 : 'FILE_ID_ALREADY_EXISTS',
    0x6A8A : 'DF_NAME_ALREADY_EXISTS',
    # Checking errors.
    0x6B00 : 'WRONG_PARAMETERS_P1_P2',
    0x6D00 : 'INVALID_INSTRUCTION_OR_NOT_SUPPORTED',
    0x6E00 : 'CLASS_NOT_SUPPORTED',
    0x6F00 : 'TECHNICAL_PROBLEM',
    # 2G/GSM codes.
    0x9400 : 'GSM_COMMAND_NOT_ALLOWED_NO_EF_SELECTED',
    0x9402 : 'GSM_INVALID_DATA_ADDRESS', #SC
    0x9404 : 'GSM_FILE_NOT_FOUND',
    0x9408 : 'GSM_COMMAND_INCOPATIBLE_WITH_FILE_STRUCTURE',
    0x9802 : 'GSM_CHV_NOT_ACTIVE',
    0x9802 : 'GSM_CHV_IS_INVALIDATED',
    0x9804 : 'GSM_ACCESS_CONDITION_NOT_FULFILLED',
    0x9808 : 'GSM_CHV_ALREADY_VALIDATED',
    0x9810 : 'GSM_SELECTED_FILE_INVALIDATED',
    0x9840 : 'GSM_UNSUCCESSFUL_USER_PIN_VERIFICATION',
    # Applications errors.
    0x9850 : 'INCREASE_CANNOT_BE_PERFORMED_MAX_REACHED',
    0x9862 : 'AUTHENTICATION_ERROR_APPLICATION_SPECIFIC',
    0x9863 : 'SECURITY_SESSION_OR_ASSOCIATION_EXPIRED',
})

iso7816 = sym_table({
    0x04 : 'DEACTIVATE_FILE',
    0x0E : 'ERASE_BINARY',
    0x10 : 'TERMINAL_PROFILE',
    0x12 : 'FETCH',
    0x14 : 'TERMINAL_RESPONSE',
    0x20 : 'VERIFY_PIN',
    0x24 : 'CHANGE_PIN',
    0x26 : 'DISABLE_PIN',
    0x28 : 'ENABLE_PIN',
    0x2C : 'UNBLOCK_PIN',
    0x32 : 'INCREASE',
    0x44 : 'ACTIVATE_FILE',
    0x70 : 'MANAGE_CHANNEL',
    0x73 : 'MANAGE_SECURE_CHANNEL',
    0x75 : 'TRANSACT_DATA',
    0x82 : 'EXTERNAL_AUTHENTICATE',
    0x84 : 'GET_CHALLENGE',
    0x88 : 'INTERNAL_AUTHENTICATE',
    0x89 : 'INTERNAL_AUTHENTICATE2',
    0xA2 : 'SEARCH_RECORD',
    0xA4 : 'SELECT_FILE',
    0xAA : 'TERMINAL_CAPABILITY',
    0xB0 : 'READ_BINARY',
    0xB2 : 'READ_RECORD',
    0xC0 : 'GET_RESPONSE',
    0xC2 : 'ENVELOPE',
    0xCB : 'RETRIEVE_DATA',
    0xCA : 'GET_DATA',
    0xD0 : 'WRITE_BINARY',
    0xD2 : 'WRITE_RECORD',
    0xD4 : 'RESIZE_FILE',
    0xD6 : 'UPDATE_BINARY',
    0xDA : 'PUT_DATA',
    0xDB : 'SET_DATA',
    0xDC : 'UPDATE_RECORD',
    0xE0 : 'CREATE_FILE',
    0xE2 : 'APPEND_RECORD',
    0xE4 : 'DELETE_FILE',
    0xF2 : 'STATUS',
})

# ETSI TS 102 223 - 9.4
proactive_command = sym_table({
    0x03 : 'POLL_INTERVAL',
    0x13 : 'SEND_SHORT_MESSAGE',
    0x16 : 'GEOGRAPHICAL_LOCATION_REQUEST',
})

# ETSI TS 101 220 - 7.2 Assigned TLV tag values
# Card application toolkit templates
cat = sym_table({
    0xD0 : 'PROACTIVE_COMMAND',
    0xD1 : 'SMS_PP_DOWNLOAD',
})

# ETSI TS 101 220 - 7.2 Assigned TLV tag values
# Card application toolkit data objects
cat_data = sym_table({
    0x81 : 'COMMAND_DETAILS',
    0x82 : 'DEVICE_IDENTITY',
    0x0B : 'SMS_PDU',
})

# ETSI TS 101 220 - 7.2 Assigned TLV tag values
# Proprietary information ('A5')
properietaryTag = sym_table({
    0x80 : 'UICC_CHARACTERISTICS',
    0x81 : 'APP_POWER_CONSUMPTION',
    0x82 : 'MIN_APP_CLOCK_FREQ',
    0x83 : 'AMOUNT_OF_AVAIL_MEMORY',
    0x84 : 'FILE_DETAILS',
    0x85 : 'RESERVED_FILE_SIZE',
    0x86 : 'MAXIMUM_FILE_SIZE',
    0x87 : 'SUPPORTED_SYSTEM_COMMANDS',
    0x88 : 'SPECIFIC_UICC_ENV_CONDITIONS'
})

# ETSI TS 101 220 - 7.2 Assigned TLV tag values
# PIN Status data objects ('C6')
pinStatusTag = sym_table({
    0x83 : 'KEY_REFERENCE',
    0x90 : 'PIN_STATUS',
    0x95 : 'USAGE_QUALIFIER',
})

#ts_102221v080200p 11.1.1.3 Response Data
selectTag = sym_table({
    0x62 : "FCP",
    0x80 : "FILE_SIZE",
    0x81 : "TOTAL_FILE_SIZE",
    0x82 : "FILE_DESCRIPTOR",
    0x83 : "FILE_IDENTIFIER",
    0x84 : "DF_NAME",
    0x88 : "SHORT_FILE_IDENTIFIER",
    0x8A : "LIFE_CYCLE_STATUS",
    0x8B : "SECURITY_ATRIBUTES_COMPACT",
    0x8C : "SECURITY_ATRIBUTES_REF_EXPANDED",
    0xAB : "SECURITY_ATRIBUTES_EXPANDED",
    0xA5 : "PROPRIETARY_INF",
    0xC6 : "PIN_STATUS_TEMPLATE",
})

#ts_102221v080200p  Table 11.5: File descriptor byte
fileDecriptorMask = sym_table({
    0b01000000 : "FILE_ACCESSIBILITY",
    0b00111000 : "FILE_TYPE",
    0b00000111 : "EF_STRUCTURE"
})

#ts_102221v080200p  Table 11.5: File descriptor byte
fileDescriptor = sym_table({
    0b00000000 : "NOT_SHAREABLE",
    0b01000000 : "SHAREABLE",
    0b00000000 : "WORKING_EF",
    0b00010000 : "INTERNAL_EF",
    0b00111000 : "DF_OR_ADF",
    0b00000000 : "NO_INFORMATION_GIVEN", #b4-b6 not all set to 1
    0b00000001 : "TRANSPARENT_STRUCTURE",
    0b00000010 : "LINEAR_FIXED_STRUCTURE",
    0b00000110 : "CYCLIC_STRUCTURE",
    #refactor, cannot be the same value as TRANSPARENT_STRUCTURE
    #0b00000001 : "BER_TLV_STRUCTURE", #b4-b6 all set to 1
})

# 3G specific
fileSearchType = sym_table({
    0b00000100 : "FORWARD_SEARCH_FROM_P1",
    0b00000101 : "BACKWARD_SEARCH_FROM_P1",
    0b00000110 : "ENHENCED_SEARCH",
    0b00000111 : "PROPERIETARY_SEARCH"
})

fileSearchIndication = sym_table({
    0b00000100 : "FORWARD_SEARCH_FROM_P1",
    0b00000101 : "BACKWARD_SEARCH_FROM_P1",
    0b00000110 : "FORWARD_SEARCH_FROM_NEXT_RECORD",
    0b00000111 : "BACKWARD_SEARCH_FROM_PREVIOUS_RECORD"
})

searchStartMode = sym_table({
    0b00000000 : "START_FROM_OFFSET",
    0b00001000 : "START_FROM_VALUE",
})

# 2G specific
fileSeekType = sym_table({
    0x00 : "TYPE_1",
    0x10 : "TYPE_2"
})

# with x='0' specifies type 1 and x='1' specifies type 2 of the SEEK command
fileSeekMode = sym_table({
    0x00 : "FROM_THE_BEGINNING_FORWARD",
    0x01 : "FROM_THE_END_BACKWARD",
    0x02 : "FROM_THE_NEXT_LOCATION_FORWARD",
    0x03 : "FROM_THE_PREVIOUS_LOCATION_BACKWARD",
})

verifyChvP2_3g = sym_table({
    0x01 : "chv1", # PIN1
    0x81 : "chv2", # PIN2
    0x0A : "adm1",
    0x0B : "adm2",
    0x0C : "adm3",
    0x0D : "adm4",
})

# 2G specific
verifyChvP2_2g = sym_table({
    0x01 : "chv1",
    0x02 : "chv2",
    0x0B : "adm1",
})

# 2G specific
verifyChvUnblockP2 = sym_table({
    0x00 : "chv1",
    0x02 : "chv2"
})

readRecordSelect = sym_table({
    0b00000000 : "CURRENT_EF",
    0b11111000 : "SFI",
})

readRecordMode = sym_table({
    0b00000010 : "NEXT_RECORD",
    0b00000011 : "PREVIOUS_RECORD",
    0b00000100 : "ABSOLUTE_OR_CURRENT",
})

binaryCmdP1 = sym_table({
    0b10000000 : "SFI_MODE",
    0b00000111 : "SFI_MASK",
})

adfName = sym_table({
    0x02 : 'ADF_USIM',
    0x04 : 'ADF_ISIM'
})
