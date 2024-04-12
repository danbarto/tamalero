import os
import random
from tamalero.utils import read_mapping, get_config
from functools import wraps
try:
    from tabulate import tabulate
    has_tabulate = True
except ModuleNotFoundError:
    print ("Package `tabulate` not found.")
    has_tabulate = False

def channel_byname(channel_func):
    @wraps(channel_func)
    def wrapper(mux64, channel):
        if isinstance(channel, str):
            channel_dict = mux64.channel_mapping
            pin = channel_dict[channel]['pin']
            return channel_func(mux64, pin)
        elif isinstance(channel, int):
            return channel_func(mux64, channel)
        else:
            invalid_type = type(channel)
            raise TypeError(f"{channel_func.__name__} can only take positional arguments of type int or str, but argument of type {invalid_type} was given.")
    return wrapper

def channel_bypin(channel_func):
    @wraps(channel_func)
    def wrapper(mux64, value, channel):
        if isinstance(channel, int):
            channel_dict = mux64.channel_mapping
            for ch in channel_dict.keys():
                if channel_dict[ch]["pin"] == channel:
                    name = ch
                    break
            return channel_func(mux64, value, ch)
        elif isinstance(channel, str):
            return channel_func(mux64, value, channel)
        else:
            invalid_type = type(channel)
            raise TypeError(f"{channel_func.__name__} can only take positional arguments of type int or str, but argument of type {invalid_type} was given.")
    return wrapper

class MUX64:

    def __init__(self, rb=0, ver=0, config='default', rbver=None, LPGBT=None, SCA=None):
        self.rb = rb
        self.ver = 1  # NOTE same as for SCA, we're giving it the lpGBT version (bur for the moment not used)
        self.config = config
        self.LPGBT = LPGBT
        self.SCA = SCA
        self.rbver = rbver

        self.configure()

        if self.rbver and self.rbver < 3:
            print("This MUX64 is associated to an old version of the Readout Board")

        if LPGBT and SCA:
            print("MUX64 is connected to both LPGBT and SCA: Please pick one")


    def is_connected(self):
        if self.LPGBT:
            print("Connected to LPGBT")
            return 1
        elif self.SCA:
            print("Connected to SCA")
            return 1
        else:
            return 0


    def configure(self):
        self.set_channel_mapping()
        if self.LPGBT:
            for p in range(1, 6+1):
                self.LPGBT.set_gpio_direction(f"MUXCNT{p}", 1)


    def set_channel_mapping(self):
        self.channel_mapping = get_config(self.config, version=f'v{self.rbver}')['MUX64']['channel']
   
    @channel_bypin
    def volt_conver(self,value,channel):
        if self.SCA:
            voltage = (value / (2**12 - 1) ) * self.channel_mapping[channel]['conv']
        elif self.LPGBT:
            value_calibrated = value * self.LPGBT.cal_gain / 1.85 + (512 - self.LPGBT.cal_offset)
            input_voltage = value_calibrated / (2**10 - 1) * self.LPGBT.adc_mapping['MUX64OUT']['conv']
            voltage = input_voltage * self.channel_mapping[channel]['conv']
        else:
            voltage = 0.0
        return voltage

    @channel_byname
    def read_adc(self, channel):

        #channel select
        s0 = (channel & 0x01)
        s1 = (channel & 0x02) >> 1
        s2 = (channel & 0x04) >> 2
        s3 = (channel & 0x08) >> 3
        s4 = (channel & 0x10) >> 4
        s5 = (channel & 0x20) >> 5

        if self.SCA:
            self.SCA.set_gpio('mux_addr0', s0)
            self.SCA.set_gpio('mux_addr1', s1)
            self.SCA.set_gpio('mux_addr2', s2)
            self.SCA.set_gpio('mux_addr3', s3)
            self.SCA.set_gpio('mux_addr4', s4)
            self.SCA.set_gpio('mux_addr5', s5)
            value = self.SCA.read_adc(0x12)

        if self.LPGBT:
            self.LPGBT.set_gpio('MUXCNT1', s0)
            self.LPGBT.set_gpio('MUXCNT2', s1)
            self.LPGBT.set_gpio('MUXCNT3', s2)
            self.LPGBT.set_gpio('MUXCNT4', s3)
            self.LPGBT.set_gpio('MUXCNT5', s4)
            self.LPGBT.set_gpio('MUXCNT6', s5)
            self.LPGBT.init_adc()
            value = self.LPGBT.read_adc(self.LPGBT.adc_mapping['MUX64OUT']['pin'])
        
        return value

    def read_channel(self, channel):
        value = self.read_adc(channel)
        voltage = self.volt_conver(value,channel)
        return voltage

    def read_channels(self): #read and print all adc values
        self.set_channel_mapping()
        channel_dict = self.channel_mapping
        table = []
        will_fail = False
        for channel in channel_dict.keys():
            pin = channel_dict[channel]['pin']
            comment = channel_dict[channel]['comment']
            value = self.read_adc(pin)
            voltage = self.read_channel(pin)
            table.append([channel, pin, value, voltage, comment])

        headers = ["Channel","Pin", "Reading", "Voltage", "Comment"]

        if has_tabulate:
            print(tabulate(table, headers=headers,  tablefmt="simple_outline"))
        else:
            header_string = "{:<20}"*len(headers)
            data_string = "{:<20}{:<20}{:<20.0f}{:<20.3f}{:<20}"
            print(header_string.format(*headers))
            for line in table:
                print(data_string.format(*line))





