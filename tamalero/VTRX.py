'''
=== Documentation ===
Prototype:  https://edms.cern.ch/ui/file/1719330/1/VLplus_quadLDD_spec_v1.2_prototypes.pdf
Production: https://edms.cern.ch/ui/file/1719330/1/VLplus_quadLDD_spec_v1.3.pdf
'''

from tamalero.colors import conditional
import os
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


global_status_bits = {
    0: "Global Chip Enable",
    1: "Global Limiting Amplifier Enable",
    2: "Global Bias Circuit Enable",
    3: "Global Modulation Circuit Enable",
    4: "Global Pre-emphasis Enable",
}

ch_status_names = {
    'CHxEN'   : "Channel Enable",
    'CHxLAEN' : "Limiting Amplifier Enable",
    'CHxBEN'  : "Biasing Circuit Enable",
    'CHxMODEN': "Modulation Circuit Enable",
    'CHxEMPR' : "Rising Edge Pre-emphasis",
    'CHxEMPF' : "Falling Edge Pre-emphasis",
}

class VTRX:

    def __init__(self, master, disable_channels=[]):
        '''
        master: the lpGBT master to the VTRX
        '''
        self.master = master

        for ch in disable_channels:
            print (f"Disabling VTRx+ channel {ch}")
            self.disable(channel=ch)

        # if kcu is dummy kcu;
        if self.master.kcu.hw == None:
            return

        if self.rd_adr(0x15)>>4 == 1:
            self.ver = "production"
        else:
            self.ver = "prototype"
        print('VTRx+ Version is: '+self.ver)

        with open(os.path.expandvars('$TAMALERO_BASE/address_table/VTRX.yaml'), 'r') as f:
            self.regs = load(f, Loader=Loader)[self.ver]

    def reset(self, hard=False, toggle_channels=[]):
        if hard:
            # enable / disable
            self.master.set_gpio(13,1)
            self.master.set_gpio(13,0)
        # reset_b
        self.master.set_gpio(10,0)
        self.master.set_gpio(10,1)

        for ch in toggle_channels:
            self.disable(ch=ch)
            self.enable(ch=ch)

    def rd_adr(self, adr):
        return self.master.I2C_read(adr, master=2, slave_addr=0x50, adr_nbytes=1)

    def wr_adr(self, adr, data, ignore_response=False):
        self.master.I2C_write(adr, val=data, master=2, slave_addr=0x50, adr_nbytes=1, ignore_response=ignore_response)

    def rd_reg(self, reg):
        adr   = self.regs[reg]['adr']
        shift = self.regs[reg]['shift']
        mask  = self.regs[reg]['mask']
        return (self.rd_adr(adr)&mask)>>shift

    def wr_reg(self, reg, val, ignore_response=False):
        adr   = self.regs[reg]['adr']
        shift = self.regs[reg]['shift']
        mask  = self.regs[reg]['mask']
        ctrl_reg = rd_adr(adr)
        new_reg  = ((val<<shift)&mask)|(ctrl_reg&(~mask))
        self.wr_adr(adr, new_reg, ignore_response=ignore_response)

    def rd_reg_ch(self, reg, ch):
        adr   = self.regs[reg]['adr'][ch]
        shift = self.regs[reg]['shift'][ch]
        mask  = self.regs[reg]['mask'][ch]
        return (self.rd_adr(adr)&mask)>>shift

    def wr_reg_ch(self, reg, ch, val, ignore_response=False):
        adr   = self.regs[reg]['adr'][ch]
        shift = self.regs[reg]['shift'][ch]
        mask  = self.regs[reg]['mask'][ch]
        ctrl_reg = rd_adr(adr)
        new_reg  = ((val<<shift)&mask)|(ctrl_reg&(~mask))
        self.wr_adr(adr, new_reg, ignore_response=ignore_response)

    def status(self, quiet=False):
        print("\n## VTRx+ status:")

        if self.ver == "prototype":
            global_status = self.rd_adr(self.regs['GSTAT']['adr'])

            for b in global_status_bits.keys():
                print("{:40}{:>2}".format(global_status_bits[b], (global_status & 2**b)>0))
        elif self.ver == "production":
            print("VTRx+ production version does not have global statuses.")
            global_status = None

        self.channel_status()

        return global_status

    def channel_status(self):
        print("\n## VTRx+ Channel status:")

        if self.ver == "prototype":
            statuses = ['CHxEN','CHxLAEN','CHxBEN','CHxMODEN','CHxEMPR','CHxEMPF']
        elif self.ver == "production":
            statuses = ['CHxEN','CHxMODEN','CHxEMPR','CHxEMPF']

        header = [""] + ["Channel %s"%ch for ch in range(4) ]
        print("{:40}{:12}{:12}{:12}{:12}".format(*header))
        for s in statuses:
            line = [ch_status_names[s]] + [ self.rd_reg_ch(s,ch) for ch in range(4) ]
            print("{:40}{:^12}{:^12}{:^12}{:^12}".format(*line))

    def enable(self, ch=0):
        if self.ver == 'prototype' and ch == 0:
            ctrl_reg = self.regs['CHxEN']['default']
            # we can't read back if channel 0 is disabled, just set to default values
            adr      = self.regs['CHxEN']['adr'][ch]
            shift    = self.regs['CHxEN']['shift'][ch]
            self.wr_adr(adr, ctrl_reg | (1<<shift))
        else:
            self.wr_reg_ch('CHxEN', ch, 1)

    def disable(self, ch=0):
        ignore_response = True if channel == 0 else False
        if self.ver == 'prototype' and ch == 0:
            ctrl_reg = self.regs['CHxEN']['default']
            adr      = self.regs['CHxEN']['adr'][ch]
            shift    = self.regs['CHxEN']['shift'][ch]
            self.wr_adr(adr, ctrl_reg&(0xff^(1<<shift)), ignore_response=ignore_response)
        else:
            self.wr_reg_ch('CHxEN', ch, 0)

    def preemph_enable(self):
        if self.ver == "prototype":
            wr_reg('GPEN', 1)

    def preemph_disable(self):
        if self.ver == "prototype":
            wr_reg('GPEN', 0)

    def set_preemph_rising(self, ch=0, enable=True):
        if enable:
            self.wr_reg_ch('CHxEMPR', ch, 1)
        else:
            self.wr_reg_ch('CHxEMPR', ch, 0)

    def set_preemph_falling(self, channel=0, enable=True):
        if (enable):
            self.wr_reg_ch('CHxEMPF', ch, 1)
        else:
            self.wr_reg_ch('CHxEMPF', ch, 0)

    def set_bias_current(self, ch=0, current=0x2f):
        self.wr_reg_ch('CHxBIAS', ch, current)

    def set_modulation_current(self, channel=0, current=0x26):
        self.wr_reg_ch('CHxMOD', ch, current)

    def get_modulation_current(self, channel=0):
        return self.rd_reg_ch('CHxMOD', ch)

    def set_emphasis_amplitude(self, channel=0, amplitude=0x0):
        self.wr_reg_ch('CHxEMP', ch, amplitude)
