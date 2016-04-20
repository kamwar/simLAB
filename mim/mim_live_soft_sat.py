#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz <k.wartanowicz@gmail.com>

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging

from sim import sim_router
from sim import sim_card
from sim import sim_reader
from util import types

logging.basicConfig(level=logging.INFO, format='%(message)s')

simType=types.TYPE_USIM

sim1 = sim_card.SimCard()
sim1.connect(sim_reader.READER_ID_0)
atr1 = sim1.getATR()

sim2 = sim_card.SimCard(mode=sim_reader.MODE_SIM_SOFT)
sim2.connect(sim_reader.READER_ID_0)
atr2 = sim2.getATR()

simRouter = sim_router.SimRouter(cards=[sim1, sim2],
                       atr=atr1, type=simType)

# Forward SAT to sim2.
sim2.routingAttr.insReplaced = sim_card.SAT_INS
simRouter.run(mode=sim_router.ROUTER_MODE_INTERACTIVE)