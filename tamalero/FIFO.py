import os
import time
from tamalero.utils import chunk
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

def revbits(x):
    return int(f'{x:08b}'[::-1],2)

class FIFO:
    def __init__(self, rb, elink=0, ETROC='ETROC1', lpgbt=0):
        self.rb = rb
        self.ETROC = ETROC
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_ELINK_SEL"%self.rb.rb, elink)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_LPGBT_SEL"%self.rb.rb, lpgbt)
        self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.DL_SRC"%self.rb.rb, 3)
        #self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.TRIG.DOWNLINK.DL_SRC"%self.rb.rb, 3)  # This does not exist (no trigger downlink)

        for i in range(5):
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG%i"%(self.rb.rb, i), 0x00)
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG%i_MASK"%(self.rb.rb, i), 0x00)

        with open(os.path.expandvars('$TAMALERO_BASE/configs/dataformat.yaml')) as f:
            self.dataformat = load(f, Loader=Loader)[ETROC]

        with open(os.path.expandvars('$TAMALERO_BASE/configs/fast_commands.yaml')) as f:
            self.fast_commands = load(f, Loader=Loader)[ETROC]

        self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_IDLE"%self.rb.rb, self.fast_commands['IDLE'])
        self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_DATA"%self.rb.rb, self.fast_commands['L1A'])

        if ETROC == 'ETROC2':
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_REVERSE_BITS"%self.rb.rb, 0x01)
        elif ETROC == 'ETROC1':
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_REVERSE_BITS"%self.rb.rb, 0x00)


    def set_trigger(self, words, masks):  # word0=0x0, word1=0x0, word2=0x0, word3=0x0, mask0=0x0, mask1=0x0, mask2=0x0, mask3=0x0):
        assert len(words)==len(masks), "Number of trigger bytes and masks has to match"
        for i, (word, mask) in enumerate(list(zip(words, masks))):
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG%i"%(self.rb.rb, i), word)
            self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_TRIG%i_MASK"%(self.rb.rb, i), mask)

    def reset(self, l1a=False):
        # needs to be reset twice, dunno
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)
        self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_RESET"%self.rb.rb, 0x01)
        #print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_ARMED"%self.rb.rb))
        #print(self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY"%self.rb.rb))
        #self.rb.kcu.write_node("READOUT_BOARD_%s.FIFO_FORCE_TRIG" % self.rb.rb, 1)
        if self.ETROC == 'ETROC2' and l1a:
            self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_DATA"%self.rb.rb, self.fast_commands['L1A'])
            self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_PULSE"%self.rb.rb, 0x01)  # FIXME confirm this
        elif self.ETROC == 'ETROC2':
            self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_IDLE"%self.rb.rb, self.fast_commands['IDLE'])
            self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_PULSE"%self.rb.rb, 0x01)  # FIXME confirm this

    def make_word(self, bytes, reversed=False):
        if len(bytes) == 5 and not reversed:
            return bytes[0] << 32 | bytes[1] << 24 | bytes[2] << 16 | bytes[3] << 8 | bytes[4]
        elif len(bytes) == 5 and reversed:
            return bytes[0] | bytes[1] << 8 | bytes[2] << 16 | bytes[3] << 24 | bytes[4] << 32
        return 0

    def compare(self, byte, frame, mask):
        return (byte & mask) == frame

    def align_stream(self, stream):
        frames = []
        masks = []
        for shift in [32, 24, 16, 8, 0]:
            frames.append((self.dataformat['identifiers']['header']['frame'] & ((self.dataformat['identifiers']['header']['mask'] >> shift) & 0xFF) << shift) >> shift)
            masks.append((self.dataformat['identifiers']['header']['mask'] >> shift) & 0xFF)

        for i in range(250):
            word = stream[i:i+5]
            res = list(map(self.compare, word, frames, masks))
            if sum(res) == 5:
                return stream[i:]
        return []

    def dump(self, block=255, format=True):
        #self.rb.kcu.write_node("READOUT_BOARD_%s.LPGBT.DAQ.DOWNLINK.FAST_CMD_PULSE"%self.rb.rb, 0x01)  # FIXME this is not needed I think
        for i in range(10):
            if self.rb.kcu.read_node("READOUT_BOARD_%s.FIFO_EMPTY"%self.rb.rb).value() < 1: break
        res = self.rb.kcu.hw.getNode("DAQ_0.FIFO").readBlock(block)
        try:
            self.rb.kcu.hw.dispatch()
            return res.value()
        except:
            # NOTE: not entirely understood, but it seems this happens if FIFO is (suddenly?) empty
            return []

    def giant_dump(self, block=3000, subblock=255, format=True, align=True, rev_bits=False):
        stream = []
        for i in range(block//subblock):
            stream += self.dump(block=subblock, format=format)
        stream += self.dump(block=block%subblock, format=format)
        if align:
            stream = self.align_stream(stream)
        if format:
            hex_dump = [ '{0:0{1}x}'.format(r,2) for r in stream ]
            if rev_bits: hex_dump = [ '{0:0{1}x}'.format(revbits(int(r, 16)),2) for r in hex_dump ]
            return hex_dump
        else:
            return [ self.make_word(c, reversed=(self.ETROC=='ETROC2')) for c in chunk(stream, n=5) if len(c)==5 ]
        return res

    def wipe(self, hex_dump, trigger_words=['35', '55'], integer=False):
        '''
        after a dump you need to wipe
        '''
        tmp_chunks = chunk(trigger_words + hex_dump, int(self.dataformat['nbits']/8))

        # clean the last bytes so that we only keep full events
        for i in range(len(tmp_chunks)):
            if len(tmp_chunks[-1]) < self.dataformat['nbits']/8:
                tmp_chunks.pop(-1)
            else:
                break

        if integer:
            tmp_chunks = [ int(''.join(line),16) for line in tmp_chunks ]

        return tmp_chunks

    def dump_to_file(self, hex_dump, filename='dump.hex'):
        with open(filename, 'w') as f:
            for line in hex_dump:
                for w in line:
                    f.write('%s '%w)
                f.write('\n')

