from tamalero.KCU import KCU
from tamalero.ReadoutBoard import ReadoutBoard

from tamalero.SCA import SCA_CONTROL

if __name__ == '__main__':

    kcu = KCU(name="my_device",
              ipb_path="ipbusudp-2.0://192.168.0.10:50001",
              adr_table="module_test_fw/address_tables/etl_test_fw.xml")

    kcu.status()

    rb_0 = kcu.connect_readout_board(ReadoutBoard(0, trigger=False))

    rb_0.configure()
    rb_0.DAQ_LPGBT.status()

    from tamalero.utils import get_temp
    
    # Low level reading of temperatures
    # Read ADC channel 7 on DAQ lpGBT
    adc_7 = rb_0.DAQ_LPGBT.read_adc(7)/2**10

    # Read ADC channel 29 on GBT-SCA
    adc_in29 = rb_0.SCA.read_adc(29)/2**12

    print("reading ADC values:")
    rb_0.SCA.read_adcs()

    # Check what the lpGBT DAC is set to
    v_ref = rb_0.DAQ_LPGBT.read_dac()
    print ("\nV_ref is set to: %.3f V"%v_ref)

    if v_ref>0:
        print ("\nTemperature on RB RT1 is: %.3f C"%get_temp(adc_7, v_ref, 10000, 25, 10000, 3900))
        print ("Temperature on RB RT2 is: %.3f C"%get_temp(adc_in29, v_ref, 10000, 25, 10000, 3900))

    # High level reading of temperatures
    temp = rb_0.read_temp(verbose=1)
