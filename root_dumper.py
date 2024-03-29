#!/usr/bin/env python3
import argparse
import json
import ROOT as rt
from array import array
import numpy as np
import os

here = os.path.dirname(os.path.abspath(__file__))

def setVector(v_, l_):
    v_.clear()
    for i in l_:
        v_.push_back(i)

if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--input', action='store', help="Binary file to read from") # , default='output_run_10117'
    argParser.add_argument('--nevents', action='store', default=100, help="Number of events")
    args = argParser.parse_args()

    # Create an empty root file so that the merger step is always happy and does not get stuck
    output = f"/home/etl/Test_Stand/ETROC2_Test_Stand/ScopeHandler/ScopeData/ETROCData/output_run_{args.input}.root"
    print(output)
    f = rt.TFile(output, "RECREATE")
    tree = rt.TTree("pulse", "pulse")

    f_in_name = f'{here}/ETROC_output/output_run_{args.input}.json'
    if os.path.isfile(f_in_name):
        with open(f_in_name) as f_in:
            print("Reading from {}".format(f_in_name))
            jsonString = json.load(f_in)
            jsonData = json.loads(jsonString)

            event_       = array('I',[0])
            l1counter_   = array('I',[0])
            row_         = rt.std.vector[int]()
            col_         = rt.std.vector[int]()
            tot_code_    = rt.std.vector[float]()
            toa_code_    = rt.std.vector[float]()
            cal_code_    = rt.std.vector[float]()
            elink_       = rt.std.vector[float]()
            #raw_         = rt.std.vector[rt.std.string]()
            crc_         = rt.std.vector[int]()
            chipid_      = rt.std.vector[int]()
            bcid_        = rt.std.vector[int]()
            bcid_        = array("I",[0]) # rt.std.vector[int]()
            counter_a_   = rt.std.vector[int]()
            nhits_       = array('I',[0])
            nhits_trail_ = rt.std.vector[int]()

            tree.Branch("event",       event_, "event/I")
            tree.Branch("l1counter",   l1counter_, "l1counter/I")
            tree.Branch("row",         row_)
            tree.Branch("col",         col_)
            tree.Branch("tot_code",    tot_code_)
            tree.Branch("toa_code",    toa_code_)
            tree.Branch("cal_code",    cal_code_)
            tree.Branch("elink",       elink_)
            #tree.Branch("raw",         raw_)
            tree.Branch("crc",         crc_)
            tree.Branch("chipid",      chipid_)
            tree.Branch("bcid",        bcid_, "bcid/I")
            tree.Branch("counter_a",   counter_a_)
            tree.Branch("nhits",       nhits_, "nhits/I")
            tree.Branch("nhits_trail", nhits_trail_)

            for i, event in enumerate(jsonData):
                # print(event["bcid"])
                event_[0] =             event["event"]
                l1counter_[0] =         event["l1counter"]
                setVector(row_,         event["row"])
                setVector(col_,         event["col"])
                setVector(tot_code_,    event["tot_code"])
                setVector(toa_code_,    event["toa_code"])
                setVector(cal_code_,    event["cal_code"])
                setVector(elink_,       event["elink"])
                # setVector(raw_,         event["raw"])
                setVector(crc_,         event["crc"])
                setVector(chipid_,      event["chipid"])
                # print(event["bcid"])
                bcid_[0] =              int(event["bcid"][0])
                # setVector(bcid_,        event["bcid"])
                setVector(counter_a_,   event["counter_a"])
                nhits_[0] =             event["nhits"]
                # setVector(nhits_trail_, event["nhits_trail"])

                tree.Fill()

    f.WriteObject(tree, "pulse")
