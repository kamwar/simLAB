#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz <k.wartanowicz@gmail.com>

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging

from sim import sim_router
from sim import sim_card
from sim import sim_reader
from sim import sim_shell
from sim import sim_ctrl_3g
from util import types

simType=types.TYPE_USIM
CONNECT_EXTERNAL_SERVER = False
SERVER_IP = "10.28.27.200"

if CONNECT_EXTERNAL_SERVER:
    # Connect to external SIM server/reader.
    sim_reader.PYSCARD_RPC_IP_ADDRESS = SERVER_IP
    sim_reader.LOCAL_PYSCARD_SERVER = False
else:
    sim_reader.LOCAL_PYSCARD_SERVER = True # Use local reader
    logging.basicConfig(level=logging.INFO, format='%(message)s')

sim1 = sim_card.SimCard(mode=sim_reader.MODE_SIM_SOFT, type=simType)
sim1.connect(sim_reader.READER_ID_0)
atr1 = sim1.getATR()

sim2 = sim_card.SimCard(type=simType)
sim2.connect(sim_reader.READER_ID_0)
atr2 = sim2.getATR()

simRouter = sim_router.SimRouter(cards=[sim1, sim2],
                       atr=atr1, type=simType)

simRouter.run(mode=sim_router.ROUTER_MODE_DISABLED)
shell = simRouter.shell

#simRouter.copyFiles(sim2, sim1, sim_card.FILES_REG)
simRouter.copyFiles(sim2, sim1, ['EF_IMSI', 'EF_LOCI', 'EF_SMSP'])

# Select ADF_USIM on the main channel of SIM1.
# It's needed for authenticate instruction.
shell.select_sim_card("1")
shell.set_active_channel("0")
shell.cd("/ADF_USIM")
shell.set_active_channel("1")
shell.select_sim_card("0")

sim1.routingAttr.insReplaced = sim_card.SAT_INS
# Only INTERNAL_AUTHENTICATE instruction is forwarded to sim2.
sim2.routingAttr.insCommon = []
sim2.routingAttr.filesCommon = []
sim2.routingAttr.filesReplaced = []
sim2.routingAttr.insReplaced = ['INTERNAL_AUTHENTICATE']
#simRouter.run(mode=sim_router.ROUTER_MODE_INTERACTIVE)
simRouter.run(mode=sim_router.ROUTER_MODE_TELNET)
