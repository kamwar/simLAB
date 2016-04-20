#!/usr/bin/python
# LICENSE: GPL2
# (c) 2014 Kamil Wartanowicz <k.wartanowicz@gmail.com>

import sys,os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import logging

from sim import sim_router
from sim import sim_card
from sim import sim_reader
from util import hextools
from util import types

logging.basicConfig(level=logging.INFO, format='%(message)s')

readers = sim_card.SimCard().listReaders()
if "Dell" in readers[0]:
    readerFirst = sim_reader.READER_ID_0
else:
    readerFirst = sim_reader.READER_ID_1

simType=types.TYPE_USIM

sim1 = sim_card.SimCard()
sim1.removeAllReaders()
sim1.connect(readerFirst)
atr1 = sim1.getATR()

sim2 = sim_card.SimCard()
sim2.connect(not readerFirst)
atr2 = sim2.getATR()

simRouter = sim_router.SimRouter(cards=[sim1, sim2],
                       atr=atr2, type=simType)

sim2.routingAttr.filesReplaced = sim_card.FILES_REG
sim2.routingAttr.insReplaced = ['INTERNAL_AUTHENTICATE']
# Uncomment to forward SAT to sim2.
#sim2.routingAttr.insReplaced.append(sim_card.SAT_INS)
simRouter.run(mode=sim_router.ROUTER_MODE_INTERACTIVE)