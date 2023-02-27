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
    empty_frame_mask = np.array(res[0::2]) > (2**8)  # masking empty fifo entries
    len_cut = min(len(res[0::2]), len(res[1::2]))  # ensuring equal length of arrays downstream
    if len(res) > 0:
        return list (np.array(res[0::2])[:len_cut][empty_frame_mask[:len_cut]] | (np.array(res[1::2]) << 32)[:len_cut][empty_frame_mask[:len_cut]])
    else:
        return []

class FIFO:
    def __init__(self, rb, block=255):
        self.rb = rb
        self.block = 255

    def get_zero_suppress_status(self):
        return self.rb.kcu.read_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb).value()

    def enable_zero_surpress(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.ZERO_SUPRESS"%self.rb.rb, 0xfffffff)
        self.reset()

    def disable_zero_surpress(self):
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
        rate = self.rb.kcu.read_node("SYSTEM.L1A_RATE_CNT").value()
        return rate

    def send_l1a(self, count=1):
        for i in range(count):
            self.rb.kcu.write_node("SYSTEM.L1A_PULSE", 1)

    def reset(self):
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET" % self.rb.rb, 0x01)

    def read_block(self, block, dispatch=False):
        try:
            if dispatch:
                reads = self.rb.kcu.hw.getNode("DAQ_RB0").readBlock(block)
                self.rb.kcu.dispatch()
                return reads
            else:
                return self.rb.kcu.hw.getNode("DAQ_RB0").readBlock(block)
        except uhal_exception:
            print("uhal UDP error in FIFO.read_block")
            raise

    def read(self):
        try:
            occupancy = self.get_occupancy()
            num_blocks_to_read = occupancy // self.block
            last_block = occupancy % self.block
            data = []
            if (num_blocks_to_read):
                reads = num_blocks_to_read * [self.read_block(self.block)] + [self.read_block(last_block)]
                self.rb.kcu.hw.dispatch()
                for read in reads:
                    data += read.value()
            return data

        except uhal_exception:
            print("uhal UDP error in daq")
            return []

    def get_occupancy(self):
        try:
            return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_OCCUPANCY").value()
        except uhal_exception:
            print("uhal UDP error in FIFO.get_occupancy")
            raise

    def get_lost_word_count(self):
        return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.RX_FIFO_LOST_WORD_CNT").value()

    def get_packet_rx_rate(self):
        return self.rb.kcu.read_node(f"READOUT_BOARD_{self.rb.rb}.PACKET_RX_RATE").value()

    def get_l1a_rate(self):
        return self.rb.kcu.read_node(f"SYSTEM.L1A_RATE_CNT").value()

    def pretty_read(self, df):
        merged = merge_words(self.read())
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
