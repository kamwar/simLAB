#!/usr/bin/python
# LICENSE: GPL2
# (c) 2013 Tom Schouten <tom@getbeep.com>
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

simCard = sim_card.SimCard()
simCard.removeAllReaders()
simCard.connect(sim_reader.READER_ID_0)

simRouter = sim_router.SimRouter(cards=[simCard],
                       atr=None,
                       type=simType)
simRouter.run(mode=sim_router.ROUTER_MODE_INTERACTIVE)
