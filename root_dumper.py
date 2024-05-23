#!/usr/bin/env python3
import argparse
import json
import ROOT as rt
from array import array
import numpy as np
import os
import re
import glob
import time

def setVector(v_, l_):
    v_.clear()
    for i in l_:
        v_.push_back(i)

def dump_to_root(output_root_path, input_file, link_path):
    # Create an empty root file so that the merger step is always happy and does not get stuck
    filename = os.path.basename(input_file)
    name, ext = os.path.splitext(filename)
    if ext != '.json':
        raise ValueError("Inputted file needs to be json from data dumper")

    output = os.path.join(output_root_path, name +'.root')

    f = rt.TFile(output, "RECREATE")
    tree = rt.TTree("pulse", "pulse")

    if os.path.isfile(input_file):
        with open(input_file) as f_in:
            print("Now reading from {}".format(input_file))
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
            #crc_         = rt.std.vector[int]()
            chipid_      = rt.std.vector[int]()
            bcid_        = rt.std.vector[int]()
            bcid_        = array("I",[0]) # rt.std.vector[int]()
            #counter_a_   = rt.std.vector[int]()
            nhits_       = rt.std.vector[int]()
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
            #tree.Branch("crc",         crc_)
            tree.Branch("chipid",      chipid_)
            tree.Branch("bcid",        bcid_, "bcid/I")
            #tree.Branch("counter_a",   counter_a_)
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
                #setVector(crc_,         event["crc"])
                setVector(chipid_,      event["chipid"])
                # print(event["bcid"])
                bcid_[0] =              int(event["bcid"][0])
                # setVector(bcid_,        event["bcid"])
                #setVector(counter_a_,   event["counter_a"])
                nhits_ =             event["nhits"]
                # setVector(nhits_trail_, event["nhits_trail"])

                tree.Fill()
    f.WriteObject(tree, "pulse")
    print(f"Output written to {output} ...")
    lnk_cmd = f"ln -s {output} {link_path}{name}.root"
    os.system(lnk_cmd)
    print(f"and linked back to {link_path}{name}.root\n")

if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--input_file', action='store', help="Input full path to json file to be dumped") # , default='output_run_10117'
    args = argParser.parse_args()

    input_json_path = '/home/etl/Test_Stand/module_test_sw/ETROC_output/' #from data_dumper
    output_root_path = '/media/etl/Storage/ScopeHandler/ScopeData/ETROCData/' #to here
    linking_path = '/home/etl/Test_Stand/ETROC2_Test_Stand/ScopeHandler/ScopeData/ETROCData/'

    while True:
        if args.input_file:
            dump_to_root(output_root_path, args.input_file, linking_path)
            break
        else:
            json_files = glob.glob(input_json_path+'/*_rb*.json')
            #new json is all the json files that have not been converted to root
            new_json = [f_jsn for f_jsn in json_files if os.path.splitext(os.path.basename(f_jsn))[0]+'.root' not in os.listdir(output_root_path)]
            print("Root dumping...")
            print('\n'.join(new_json))

            for f_jsn in new_json:
                #need rb0 for bad implementation reasons, contains both rb merged ETROC
                #this line in merge_scope_etroc etroc_tree = f"{base}/ScopeData/ETROCData/output_run_{f_index}_rb0.root"
                filename = os.path.basename(f_jsn)
                name, f_ext = os.path.splitext(filename)

                dump_to_root(output_root_path, f_jsn, linking_path)
    
        print("Next check in 15 seconds")
        time.sleep(15)
        
