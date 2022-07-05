# ╔═╗╔═╗╔═╗╔╦╗╦ ╦╔═╗╦═╗╔═╗  ╔═╗╔╦╗╦═╗╔═╗╔═╗╔═╗
# ╚═╗║ ║╠╣  ║ ║║║╠═╣╠╦╝║╣   ║╣  ║ ╠╦╝║ ║║  ╔═╝
# ╚═╝╚═╝╚   ╩ ╚╩╝╩ ╩╩╚═╚═╝  ╚═╝ ╩ ╩╚═╚═╝╚═╝╚═╝

import numpy as np
import os
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


maxpixel = 256

class software_ETROC2():
    def __init__(self, BCID=0):
        print('initiating fake ETROC2...')
        
        with open(os.path.expandvars('$TAMALERO_BASE/configs/dataformat.yaml'), 'r') as f:
            self.format = load(f, Loader=Loader)['ETROC2']

        self.data = {
                'l1counter' : 0,
                'bcid'      : BCID,
                'type'      : 0,  # use type regular data
                'chipid'    : 0,
                'status'    : 0,
                'hits'      : 0,
                'crc'       : 0,
                }

        # threshold voltage
        self.vth = 198
        
        # data from most recent L1A (list of formatted words)
        self.L1Adata = []

        # number of bits in a word
        self.nbits = self.format['nbits']

        # generate fake baseline/noise properties per pixel
        self.bl_means  = [np.random.normal(198, .8) for x in range(maxpixel)]
        self.bl_stdevs = [np.random.normal(  1, .2) for x in range(maxpixel)]

        # emulated "registers"
        self.data_stor = {0x0: 0  # test register
                }


    # emulating I2C connections
    def I2C_write(self, reg, val):
        self.data_stor[reg] = val
        return None


    def I2C_read(self, reg):
        return self.data_stor[reg]


    def set_vth(self, vth):
        print('Vth set to %f...'%vth)
        self.vth = vth
        return


    # add hit data to self.L1Adata & increment hit counter
    def add_hit(self,pix):
        matrix_w = int(round(np.sqrt(maxpixel))) # pixels in NxN matrix
        data = {
                'ea'     : 0,
                'row_id' : pix%matrix_w,
                'col_id' : int(np.floor(pix/matrix_w)),
                'toa'    : np.random.randint(0,500),
                'cal'    : np.random.randint(0,500),
                'tot'    : np.random.randint(0,500),
                }
        
        word = self.format['identifiers']['data']['frame']
        for datatype in data:
            word = ( word +
                ((data[datatype]<<self.format['data']['data'][datatype]['shift'])
                &self.format['data']['data'][datatype]['mask']) )
        self.L1Adata.append(word)

        self.data['hits'] += 1

        return None


    # run one L1A
    def runL1A(self):
        self.data['hits'] = 0
        self.L1Adata = [] # wipe previous L1A data
        self.data['l1counter'] += 1

        for pix in range(maxpixel):
            # produce random hit
            val = np.random.normal(self.bl_means[pix], self.bl_stdevs[pix]) 
            # if we have a hit
            if val > self.vth :
                self.add_hit(pix)
        
        data = self.get_data()
        return data
    

    # run N L1As and return all data from them
    def run(self, N):
        data = []
        for i in range(N):
            self.runL1A()
            data += self.get_data()
        return data


    # return full data package (list of words) for most recent L1A
    def get_data(self):
        # form header word
        header = self.format['identifiers']['header']['frame']
        for datatype in ['l1counter', 'type', 'bcid']:
            header = ( header +
                ((self.data[datatype]<<self.format['data']['header'][datatype]['shift'])
                &self.format['data']['header'][datatype]['mask']) )

        # form trailer word
        trailer = self.format['identifiers']['trailer']['frame']
        for datatype in ['chipid', 'status', 'hits', 'crc']:
            trailer = ( trailer +
                ((self.data[datatype]<<self.format['data']['trailer'][datatype]['shift'])
                &self.format['data']['trailer'][datatype]['mask']) )
        return [header] + self.L1Adata + [trailer]
