from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import header, make_version_header
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame

from tamalero.SCA import SCA_CONTROL

import os
import time
import random
import sys
import numpy as np
from yahist import Hist1D, Hist2D
import logging

def build_events(dump, ETROC="ETROC1"):
    df = DataFrame(ETROC)

    events = []
    last_type = "filler"
    for word in dump:
        data_type, res = df.read(word)
        if data_type == "header" and last_type in ["trailer", "filler"]:
            events.append({"header": [], "data": [], "trailer": []})
        elif data_type == "filler":
            events.append({"filler": []})
        if len(events) > 0:
            events[-1][data_type].append(res)
        
        last_type = data_type

    return events

def get_parity(n):
    parity = 0
    while n :
        parity ^= n & 1
        n >>=  1
    return parity

if __name__ == '__main__':

    import argparse

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--kcu', action='store', default="192.168.0.10", help="Specify the IP address for KCU")
    argParser.add_argument('--read_fifo', action='store', default=2, help='Read 3000 words from link N')
    argParser.add_argument('--etroc', action='store', default='ETROC1', help='Select ETROC version')
    argParser.add_argument('--triggers', action='store', default=10, help='How many L1As?')
    argParser.add_argument('--log_level', default="INFO", type=str,help="Level of information printed by the logger")
    args = argParser.parse_args()

    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging,args.log_level.upper()))
    logger.addHandler(logging.StreamHandler())

    kcu = KCU(name="my_device",
              ipb_path="ipbusudp-2.0://%s:50001"%args.kcu,
              adr_table="module_test_fw/address_tables/etl_test_fw.xml")

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0))

    
    fifo_link = int(args.read_fifo)

    events = []
    fifo = FIFO(rb_0, elink=fifo_link, ETROC=args.etroc)
    df = DataFrame(args.etroc)
    fifo.set_trigger(
        df.get_trigger_words(),
        df.get_trigger_masks(),
    )
    
    for i in range(int(args.triggers)):
        #print(i)
        fifo.reset()
        test = fifo.giant_dump(block=300, format=False, align=(args.etroc=='ETROC1'))
        events += build_events(test, ETROC=args.etroc)

    hits = np.zeros((16,16))
    nhits = Hist1D(bins=np.linspace(-0.5,20.5,22))
    toa = Hist1D(bins=np.linspace(-0.5,2**10,50))
    tot = Hist1D(bins=np.linspace(0,2**9,50))
    #hit_matrix = Hist2D(bins=(np.linspace(-0.5,15.5,17), np.linspace(-0.5,15.5,17)))
    evnt_cnt=0
    weird_evnt=[]
    for event in events:
        if 'filler' in event: continue
        try:
            nhits.fill([event['trailer'][0]['hits']])
            if event['trailer'][0]['hits'] > 0:
                if event['trailer'][0]['hits'] != len(event['data']):
                    logger.warning(" in event {} #hits in data doesn't match trailer info".format(evnt_cnt))
                    logger.warning("data {} trailer {}".format(event['trailer'][0]['hits'],len(event['data'])))
                    weird_evnt.append(evnt_cnt)

                if args.etroc=='ETROC1':
                    trailer_parity = (1 ^ get_parity(event['trailer'][0]['hits']))
                    if trailer_parity != event['trailer'][0]['parity']:
                        logger.warning(" in event {} trailer parity and parity bit do not match".format(evnt_cnt))
                        logger.warning("computed parity {} parity bit {}".format(trailer_parity,event['trailer'][0]['parity']) )
                        weird_evnt.append(evnt_cnt)

                for d in event['data']:
                    row, col = d['row_id'], d['col_id']
                    if not args.etroc=='ETROC2':  # NOTE: not working for ETROC2 yet
                        toa.fill([d['toa']])
                        tot.fill([d['tot']])
                    hits[row, col] += 1

                    if args.etroc=='ETROC1': # FIXME: [DS] consistency checks for ETROC2 not implemented. Should this rather live somewhere else?
                        data_parity = (1 ^ get_parity(d['row_id']) ^ get_parity(d['col_id']) ^
                                       get_parity(d['toa']) ^ get_parity(d['tot']) ^
                                       get_parity(d['cal']))
                        if data_parity != d['parity']:
                            logger.warning(" in event {} data parity and parity bit do not match".format(evnt_cnt))
                            logger.warning("computed parity {} parity bit {}".format(data_parity,d['parity']) )
                            weird_evnt.append(evnt_cnt)
               
        except IndexError:
            logger.info("\nSkipping event {}, incomplete".format(evnt_cnt))
            logger.debug("header : {}".format(event['header']))
            logger.debug("data : {}".format(event['data']))
            logger.debug("trailer : {}".format(event['trailer']))
            pass
        evnt_cnt+=1 
        if evnt_cnt % 100 == 0: logger.debug("===>{} events processed".format(evnt_cnt))

    # LET THE PLOTTING BEGIN!

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_dir = os.path.join(
        "plots",
        args.etroc,
        "link_{}".format(args.read_fifo),
        timestamp,
    )
    os.makedirs(plot_dir)

    logger.info("\n Making plots for {} events with a total of {} hits".format(evnt_cnt,nhits.integral))
    import matplotlib.pyplot as plt
    import mplhep as hep

    plt.style.use(hep.style.CMS)  # or ATLAS/LHCb
    
    fig, ax = plt.subplots(1,1,figsize=(7,7))
    nhits.plot(show_errors=True, color="blue", label='Number of hits')
    ax.set_ylabel('Count')
    ax.set_xlabel('Hits')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'nhits'
    
    fig.savefig(os.path.join(plot_dir, "{}.pdf".format(name)))
    fig.savefig(os.path.join(plot_dir, "{}.png".format(name)))


    fig, ax = plt.subplots(1,1,figsize=(7,7))
    toa.plot(color="blue", histtype="step")
    ax.set_ylabel('Count')
    ax.set_xlabel('TOA')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'TOA'
    
    fig.savefig(os.path.join(plot_dir, "{}.pdf".format(name)))
    fig.savefig(os.path.join(plot_dir, "{}.png".format(name)))


    fig, ax = plt.subplots(1,1,figsize=(7,7))
    tot.plot(color="blue", histtype="step")
    ax.set_ylabel('Count')
    ax.set_xlabel('TOT')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'TOT'
    
    fig.savefig(os.path.join(plot_dir, "{}.pdf".format(name)))
    fig.savefig(os.path.join(plot_dir, "{}.png".format(name)))


    fig, ax = plt.subplots(1,1,figsize=(7,7))
    hit_matrix = Hist2D.from_bincounts(hits, bins=(np.linspace(-0.5,15.5,17), np.linspace(-0.5,15.5,17)))
    hit_matrix.plot(logz=False, cmap="cividis")
    ax.set_ylabel('Row')
    ax.set_xlabel('Column')
    
    fig.text(0.0, 0.995, '$\\bf{CMS}$ ETL', fontsize=20,  horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes )
    
    name = 'hit_matrix'
    
    fig.savefig(os.path.join(plot_dir, "{}.pdf".format(name)))
    fig.savefig(os.path.join(plot_dir, "{}.png".format(name)))
    

    #try:
    #    hex_dump = fifo.giant_dump(3000,255)
    #except:
    #    print ("Dispatch failed, trying again.")
    #    hex_dump = fifo.giant_dump(3000,255)

    #print (hex_dump)
    #fifo.dump_to_file(fifo.wipe(hex_dump, trigger_words=[]))  # use 5 columns --> better to read for our data format
