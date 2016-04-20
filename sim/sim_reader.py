#!/usr/bin/python
# Wrapper to pyscard
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz

from util import types
import logging
import threading
import zerorpc
from zerorpc.exceptions import *
from sim_soft import sim_soft_ctrl
from sim import pyscard_rpc_ctrl

PYSCARD_RPC_IP_ADDRESS = "10.28.27.200"
PYSCARD_RPC_PORT = 4148

MODE_PYSCARD = 0
MODE_SIM_SOFT = 1

LOCAL_PYSCARD_SERVER = True
MESSAGE_TIMEOUT = 60#sec

class SimReader(object):
    def __init__(self, mode=MODE_PYSCARD, type=types.TYPE_USIM):
        self.mode = mode
        self.type = type
        self.server = None
        address=PYSCARD_RPC_IP_ADDRESS
        if mode == MODE_PYSCARD and LOCAL_PYSCARD_SERVER:
            logging.debug("Pyscard local server")
            self.server = pyscard_rpc_ctrl.PyscardRpcServerThread(PYSCARD_RPC_PORT)
            self.server.setDaemon(True)
            self.server.start()
            #set locall IP addr
            address = "127.0.0.1"
        self.address = address
        self.handlers = {}

    def close(self):
        threadId = threading.current_thread().ident
        if threadId in self.handlers.keys():
            try:
                self.handlers[threadId].close()
            except:
                pass
            del self.handlers[threadId]
        if self.server:
            self.server.close()

    def runClient(self, endpoint):
        # TODO: check that client might be connected otherwise kill server
        client = zerorpc.Client(heartbeat=None, timeout=MESSAGE_TIMEOUT)
        logging.debug("Pyscard RPC client: %r" %endpoint)
        client.connect(endpoint)
        return client

    def getHandler(self):
        if self.mode == MODE_SIM_SOFT:
            if len(self.handlers):
                # TODO: remove type from SimPyscard.
                # Return first element in dict.
                return self.handlers.itervalues().next()
        threadId = threading.current_thread().ident
        if threadId not in self.handlers.keys():
            if self.mode != MODE_SIM_SOFT:
                self.handlers.update({threadId : self.runClient("tcp://"+self.address+":"+str(PYSCARD_RPC_PORT))})
            else:
                self.handlers.update({threadId : sim_soft_ctrl.SimSoftCtrl(type=self.type)})
        return self.handlers[threadId]

    def __getattr__(self,attr):
        #__getattr__ is called when undefined method of class is called
        handler = self.getHandler()
        orig_attr = getattr(handler, attr)

        if not callable(orig_attr):
            #means the objct is: function, method or callable class
            #if orig_attr is not callable (not False) return attribute (e.g. class variable)
            return orig_attr

        def hooked(*args, **kwargs):
            result = 0
            try:
                result = orig_attr(*args, **kwargs)
                #if result == handler:
                    # prevent wrapped_class from becoming unwrapped
                #    return self
            except TimeoutExpired as exceptionObj:
                logging.warning("Timeout, repeat the last command")
                try:
                    result = orig_attr(*args, **kwargs)
                except TimeoutExpired as exceptionObj:
                    raise Exception(attr + "() failed!\n" + exceptionObj.message)
            except Exception as e:
                #catch every exception except TimeoutExpired(caught above)
                e = "".join(str(e)).rstrip("\n\n")
                e = e.split("\n")
                if len(e) >= 6:
                    #limit stack
                    e = e[-6:]
                raise Exception("%s() failed!\n%s" %(attr, "\n".join(e)))
            return result
        return hooked

READER_ID_0 = 0
READER_ID_1 = 1
READER_ID_2 = 2
READER_ID_3 = 3