import struct
import os
import time
import numpy as np
from tamalero.utils import chunk
from yaml import load, dump
from tamalero.DataFrame import DataFrame
from uhal._core import exception as uhal_exception

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def revbits(x):
    return int(f'{x:08b}'[::-1],2)

def merge_words(res):
    '''
    this function merges 32 bit words from the fifo into 64 bit words (40bit ETROC2 + added meta data in the DAQ)
    it strips empty entries and removes orphan 32 bit words that could be present at the end of a FIFO read
    '''
    if len(res) > 0:
        # offset is only needed when zero suppression is turned off, and packet boundaries are not defined
        # it relies on the fact that the second 32 bit word is half empty (8 bit ETROC data + 12 bits meta data)
        # if we ever add more meta data this has to be revisited
        #offset = 1 if (res[1] > res[0]) else 0
        offset = 0
        #print(f"## Offset is {offset=}")
        #offset = 0
        res = res[offset:]
        #empty_frame_mask = np.array(res[0::2]) > (2**8)  # masking empty fifo entries
        #print(res)
        empty_frame_mask = np.array(res[0::2]) > 0  # masking empty fifo entries FIXME verify that this does not cause troubles! remove mask if possible
        len_cut = min(len(res[0::2]), len(res[1::2]))  # ensuring equal length of arrays downstream
        return list (np.array(res[0::2])[:len_cut][empty_frame_mask[:len_cut]] | (np.array(res[1::2]) << 32)[:len_cut][empty_frame_mask[:len_cut]])
    else:
        return []

class FIFO:
    def __init__(self, rb, block=255):
        self.rb = rb
        self.block = block
        if rb != None:
            self.reset()

    def ready(self):
        self.rb.kcu.write_node("READOUT_BOARD_0.ERR_CNT_RESET", 0x1)
        tmp_err_cnt = self.rb.kcu.read_node("READOUT_BOARD_%s.ERROR_CNT"%self.rb.rb).value()
        start_time = time.time()
        while tmp_err_cnt != self.rb.kcu.read_node("READOUT_BOARD_%s.ERROR_CNT"%self.rb.rb).value():
            print("Redoing bitslip")
            self.reset()
            self.enable_bitslip()
            time.sleep(0.1)
            self.disable_bitslip()
            self.rb.kcu.write_node("READOUT_BOARD_0.ERR_CNT_RESET", 0x1)
            tmp_err_cnt = self.rb.kcu.read_node("READOUT_BOARD_%s.ERROR_CNT"%self.rb.rb).value()

            if time.time() > start_time + 2:
                print("Time out, FIFO might not work as expected.")
                break

        return True

    def enable_bitslip(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.BITSLIP_AUTO_EN"%self.rb.rb, 0x1)

    def disable_bitslip(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.BITSLIP_AUTO_EN"%self.rb.rb, 0x0)

    def get_zero_suppress_status(self):
        return self.rb.kcu.read_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb).value()

    def enable_zero_surpress(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb, 0xfffffff)
        self.reset()

    def disable_zero_surpress(self, only=None):
        '''
        turn off zero suppression for all channels
        use only if you only want to disable zero suppression for one elink
        '''
        if only != None:
            self.rb.kcu.write_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb, 0xfffffff ^ (1 << only))
        else:
            self.rb.kcu.write_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb, 0x0)
        self.reset()

    def use_fixed_pattern(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.RX_FIFO_DATA_SRC"%self.rb.rb, 0x1)
        self.reset()

    def use_etroc_data(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.RX_FIFO_DATA_SRC"%self.rb.rb, 0x0)
        self.reset()

    def set_trigger_rate(self, rate):
        # set rate in Hz
        rate_setting = rate / 25E-9 / (0xffffffff) * 10000
        self.rb.kcu.write_node("SYSTEM.L1A_RATE", int(rate_setting))
        time.sleep(0.5)
        return self.get_trigger_rate()

    def get_trigger_rate(self):
        rate = self.rb.kcu.read_node("SYSTEM.L1A_RATE_CNT").value()
        return rate

    def send_l1a(self, count=1):
        for i in range(count):
            try:
                self.rb.kcu.write_node("SYSTEM.L1A_PULSE", 1)
            except:
                print("Couldn't send pulse.")

    def send_QInj(self, count=1, delay=0):
        self.rb.kcu.write_node("READOUT_BOARD_%s.L1A_INJ_DLY"%self.rb.rb, delay)
        for i in range(count):
            try:
                self.rb.kcu.write_node("READOUT_BOARD_%s.L1A_QINJ_PULSE" % self.rb.rb, 0x01)
            except:
                print("Couldn't send pulse.")

    def reset(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET" % self.rb.rb, 0x01)

    def select_elink(self, elink, lpgbt=0):
        '''
        only needed for ILA debugging
        '''
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_ELINK_SEL0" % self.rb.rb, elink)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_LPGBT_SEL0" % self.rb.rb, lpgbt)

    def read_block(self, block, dispatch=False):
        success = False
        while success == False:
            try:
                if dispatch:
                    reads = self.rb.kcu.hw.getNode(f"DAQ_RB{self.rb.rb}").readBlock(block)

                    # this was tested with 5M pulses
                    self.rb.kcu.dispatch()  # changed from more udp error prone self.rb.kcu.hw.dispatch()

                    return reads
                else:
                    return self.rb.kcu.hw.getNode(f"DAQ_RB{self.rb.rb}").readBlock(block)
            except uhal_exception:
                print(f"uhal UDP error in FIFO.read_block, block size is {block}")
                raise

    def read(self, dispatch=False, verbose=False):
        #occupancy = self.get_occupancy()*4 + 2  # FIXME don't know where factor of 4 comes from??
        #if verbose: print(f"{occupancy=}")
        #num_blocks_to_read = occupancy // self.block
        #if verbose: print(f"{num_blocks_to_read=}")
        #last_block = occupancy % self.block
        #if verbose: print(f"{last_block=}")
        data = []
        while self.get_occupancy()>0:
            # FIXME checking get_occupancy all the time is slow, but this is at least not broken.
            try:
               data += self.read_block(250, dispatch=dispatch).value()
            except:
               print('Data read failed')

        #if (num_blocks_to_read or last_block):
        #    if dispatch:
        #        #while self.get_occupancy()>0:
        #        #    data += self.read_block(255, dispatch=dispatch).value()
        #        for b in range(num_blocks_to_read):
        #            #print(b)
        #            try:
        #                data += self.read_block(self.block, dispatch=dispatch).value()
        #            except uhal_exception:
        #                print("uhal UDP error in daq, full blocks")
        #                return data
        #        try:
        #            data += self.read_block(last_block, dispatch=dispatch).value()
        #        except uhal_exception:
        #            print("uhal UDP error in daq, last block")
        #            return data
        #    else:
        #        # FIXME the part below should be faster but is somehow broken now
        #        reads = num_blocks_to_read * [self.read_block(self.block, dispatch=dispatch)] + [self.read_block(last_block, dispatch=dispatch)]
        #        try:
        #            self.rb.kcu.hw.dispatch()
        #        except:
        #            print("uhal UDP error in daq")

        #        for read in reads:
        #            data += read.value()
        return data


    def get_occupancy(self):
        try:
            return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_OCCUPANCY").value()
        except uhal_exception:
            print("uhal UDP error in FIFO.get_occupancy, trying again")
            return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_OCCUPANCY").value()
            #raise

    def is_full(self):
        try:
            return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_FULL").value()
        except uhal_exception:
            print("uhal UDP error in FIFO.is_full, trying again")
            return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_FULL").value()

    def get_lost_word_count(self):
        return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_LOST_WORD_CNT").value()

    def get_packet_rx_rate(self):
        return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.PACKET_RX_RATE").value()

    def get_l1a_rate(self):
        return self.rb.kcu.read_node(f"SYSTEM.L1A_RATE_CNT").value()

    def pretty_read(self, df, dispatch=True, raw=False):
        merged = merge_words(self.read(dispatch=dispatch))
        if raw:
            return merged
        else:
            return list(map(df.read, merged))

    def stream(self, f_out, timeout=10):
        # FIXME this is WIP
        start = time.time()
        with open(f_out, mode="wb") as f:
            while True:
                data = self.read()
                f.write(struct.pack('<{}I'.format(len(data)), *data))

                timediff = time.time() - start
                if timediff > timeout:
                    break
