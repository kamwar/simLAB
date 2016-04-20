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

sim2 = sim_card.SimCard()
sim2.connect(sim_reader.READER_ID_1)
atr2 = sim2.getATR()

sim3 = sim_card.SimCard(mode=sim_reader.MODE_SIM_SOFT)
sim3.connect(sim_reader.READER_ID_0)
atr3 = sim3.getATR()

simRouter = sim_router.SimRouter(cards=[sim1, sim2, sim3],
                       atr=atr1, type=simType)

#sim2.routingAttr.filesReplaced = sim_card.FILES_REG
#sim2.routingAttr.insReplaced = ['INTERNAL_AUTHENTICATE']

# Forward SAT to sim3.
sim3.routingAttr.insReplaced = sim_card.SAT_INS

'''
When SIM is invalidated, uncomment below.
# Files which need to be the same on all sim cards.
simRouter.getMainCard(0).routingAttr.filesReplaced += ['EF_ADN', 'EF_SDN', 'EF_SMS']
# Uncomment when card resets after quering status. UE migth expect.
# Different AID after SIM card switching if UE doesn't read EF_DIR on the basic channel.
sim1.routingAttr.filesReplaced += ['EF_DIR']
sim1.routingAttr.filesReplaced = ['STATUS']
# Other SIM files which might cause problem if not the same on all cards.
sim1.routingAttr.filesReplaced = +[
    'EF_SMS', 'EF_MBDN', 'EF_EPSNSC', 'EF_MBI', 'EF_SMSS', 'EF_MWIS', 'EF_CFIS', 'EF_LI', 'EF_ELP',
    'EF_UST', 'EF_EST', 'EF_AD', 'EF_NETPAR', 'EF_ACC', 'EF_HPPLMN', 'EF_HPLMNWACT', 'EF_PLMNWACT',
    'EF_START_HFN', 'EF_THRESHOLD', 'EF_IMG', 'EF_ACM', 'EF_ACMMAX', 'EF_HIDDENKEY', 'EF_ICCID',
    'EF_CBMI', 'EF_SMSP', 'EF_FDN', 'EF_ARR', 'EF_ANR', 'EF_MSISDN', 'EF_BDN', 'EF_ADN', 'EF_SDN',
    'EF_OCI', 'EF_ICI', 'EF_MBDN', 'EF_EXT1', 'EF_EXT2', 'EF_EXT3' ]
'''
simRouter.run(mode=sim_router.ROUTER_MODE_INTERACTIVE)