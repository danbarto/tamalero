# Software for basic ETL RB, PB and module (system) tests: Tamalero

```
 ████████╗ █████╗ ███╗   ███╗ █████╗ ██╗     ███████╗███████╗
 ╚══██╔══╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝██╔════╝
    ██║   ███████║██╔████╔██║███████║██║     █████╗  ███████╗
    ██║   ██╔══██║██║╚██╔╝██║██╔══██║██║     ██╔══╝  ╚════██║
    ██║   ██║  ██║██║ ╚═╝ ██║██║  ██║███████╗███████╗███████║
    ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
```

## Software structure

```
── Control Board (KCU105)
   ├── Readout Board 0
   │   ├── LPGBT
   │   ├── SCA
   │   ├── Power Board Interface
   │   ├── Module 0
   │   │   ├── ETROC0
   │   │   ├── ETROC1
   │   │   ├── ETROC2
   │   │   └── ETROC3
   │   ├── Module 1
   │   ├── ...
   │   └── Module N
   ├── Readout Board 1
   ├── Readout Board 2
   ├── ...
   └── Readout Board 9
```


## Dependencies

Tested on python 3.8.10.
Install the software with all its dependencies except IPbus:

``` shell
git clone https://gitlab.cern.ch/cms-etl-electronics/module_test_sw.git
pip install --editable .
```

To install IPbus please see the [IPbus user guide](https://ipbus.web.cern.ch/doc/user/html/software/installation.html).

The software emulator also runs without ipbus installed.
To use a container with preinstalled dependencies, refer to [this section](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw#using-docker) (needs docker installed).

## Running the code

To properly set all paths run `source setup.sh`.

### Software only

A software emulator of ETROC2 has been implemented, and examples of its usage are implemented in `test_ETROC.py`.
The simplest example requests a handful of data words by sending L1As at different threshold values.

``` bash
ipython3 -i test_ETROC.py
```

Which should return something like

``` bash
Running without uhal (ipbus not installed with correct python bindings)
Sending 10 L1As and reading back data, for the following thresholds:
[203.0, 202.7, 202.4, 202.1, 201.8, 201.5, 201.2, 200.9, 200.6, 200.3]
Threshold at th=203.0mV
Vth set to 203.000000.
('header', {'elink': 0, 'sof': 0, 'eof': 0, 'full': 0, 'any_full': 0, 'global_full': 0, 'l1counter': 1, 'type': 0, 'bcid': 0})
('trailer', {'elink': 0, 'sof': 0, 'eof': 0, 'full': 0, 'any_full': 0, 'global_full': 0, 'chipid': 25152, 'status': 0, 'hits': 0, 'crc': 0})
Threshold at th=202.7mV
Vth set to 202.700000.
('header', {'elink': 0, 'sof': 0, 'eof': 0, 'full': 0, 'any_full': 0, 'global_full': 0, 'l1counter': 2, 'type': 0, 'bcid': 0})
('trailer', {'elink': 0, 'sof': 0, 'eof': 0, 'full': 0, 'any_full': 0, 'global_full': 0, 'chipid': 25152, 'status': 0, 'hits': 0, 'crc': 0})
Threshold at th=202.4mV
...
```

A threshold scan can be run with

``` bash
ipython3 -i test_ETROC.py -- --vth --fitplots
```

The threshold scans will produce S-curves for each pixel.
![](output/pixel_1.png)

### With a physical Readout Board

A minimal example of usage of this package with a physical readout board (v1 or v2) is given in `test_tamalero.py`, which can be run as:
`ipython3 -i test_tamalero.py`

The code is organized similar to the physical objects.
The 0th readout board object can be initialized with
```
rb_0 = ReadoutBoard(0, trigger=False, flavor='small')
```
where `trigger=False` defines that we don't deal with the trigger lpGBT (not yet fully implemented).
The current RB prototype is of the small flavor (3 modules, 12 ETROCs). We anticipate implementing different flavors in the future.

To interact with `rb_0` we need to initialize a control board (KCU105)
```
kcu = KCU(name="my_device",
          ipb_path="chtcp-2.0://localhost:10203?target=192.168.0.11:50001",
          adr_table="module_test_fw/address_tables/etl_test_fw.xml",
	  dummy=False)
```
and connect it to the readout board
```
rb_0.connect_KCU(kcu)
```

**Note:** Control hub is now required for using the KCU, as shown in the default `ipb_path` of the KCU (i.e. `"chtcp-2.0://localhost:10203?target=192.168.0.11:50001"` instead of `"ipbusudp-2.0://192.168.0.11:50001"`). `tamalero` won't run otherwise.
Control hub is part of the IPbus package and can be started with e.g. `/opt/cactus/bin/controlhub_start`.

We can then configure the RB and get a status of the lpGBT:
```
rb_0.configure()
rb_0.DAQ_LPGBT.status()
```

Now we're all set! Some high level functions are currently being implemented.
An example is the following:
```
rb_0.read_temp(verbose=1)
```
that reads the temperature of all the available sensors on the board. The output looks like this
```
V_ref is set to: 0.900 V

Temperature on RB RT1 is: 33.513 C
Temperature on RB RT2 is: 34.138 C
Temperature on RB SCA is: 32.668 C
```

One can interact with the lpGBT and SCA directly, either via `rb_0.DAQ_LPGBT` or `rb_0.SCA`.
The classes are defined in [here](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/tree/master/tamalero).

The current reading of the SCA ADCs can be obtained with
```
rb_0.SCA.read_adcs()
```
which reads all ADC lines that are connected, according to the mapping given in [configs/SCA_mapping.yaml](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/blob/master/configs/SCA_mapping.yaml) or [configs/SCA_mapping_v2.yaml](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw/-/blob/master/configs/SCA_mapping_v2.yaml) depending on the readout board version.
An example is given here:
```
adc:
    1V2_mon0:
        pin: 0x01
        conv: 1
        flavor: small
        comment: monitoring for 1.2V of ETROC0

    ...

        BV0:
        pin: 0x12
        conv: 1220
        flavor: small
        comment: monitoring for BV line 0
```
## Developing the code

While developing software for `tamalero`, it is necessary to test new features with the `tests/startup.sh` script before opening a merge request. Both `tamalero` (`setup.sh`) and Vivado must be sourced first. To use `startup.sh`, source the script and pass the appropriate options:
```
Usage:
	startup
       Options:
	[-i | --id ID]              Unique ID of CI KCU
	[-f | --firmware FIRMWARE]  Firmware version of KCU
	[-p | --psu PSU:CH]         IP address and channel(s) of Power Supply Unit (will trigger power cycle)
	[-k | --kcu KCU]            IP address of Xilinx KCU
	[-c | --cycle]		    Power cycle PSU (not necessary if -p is set)
	[-h | --help]               Show this screen
```
It is generally recommended to power cycle the Power Supply Units when testing a new feauture with `tests/startup.sh`. An example command is given below:
```
source tests/startup.sh -i 210308B0B4F5 -k 192.168.0.12 -p 192.168.2.3:ch2
```

## Fermilab test beam simulation

To use the Fermilab test beam simulation, we rely on the `Beam.py` class and the `beam_utils.py` auxiliary functions. A simple script `test_beam.py` is available for quick testing. In addition to the simulation, the Beam class implements a UI monitoring dashboard for real-time checks of useful RB parameters. To use `test_beam.py`, pass the appropriate options:
```
Usage:
        test_beam
       Options:
        [--kcu KCU]              Specify the IP address of KCU. Default: 192.168.0.11
        [--host HOST]		 Specify host for control hub. Default: localhost
        [--l1a_rate L1A_RATE]    Level-1 Accept rate in kHz. Default: 1000
        [--time TIME]            Time in minutes that the beam will run. Default: 1
        [--verbosity]            Verbosity information
        [--dashboard]            UI Monitoring dashboard on?
        [--configuration]        Specify the readout board config file from "default, emulator, modulev0". Default: default
```
`test_beam.py` will simulate Fermilab's test beam of 4s on-time and 56s off-time spills, at the specified L1A rate and number of spills. The simulation will produce a compressed zip file after each spill and save it in the `outputs` directory with a time stamp. The dashboard currently monitors the number of cycles (i.e. spills), L1A rate count, FIFO occupancy, thermistor temperatures (RT1, RT2, SCA and VTRX), lost FIFO words and packet rate. The dashboard heavily relies on the [Rich Python library](https://github.com/Textualize/rich); for development of the dashboard see [docs](https://rich.readthedocs.io/en/stable/introduction.html).

### Test beam output

![](output/TestBeamVerbosity.png)

### UI monitoring dashboard output

![](output/TestBeamDashboard.png)

## Notebook

To use the jupyter notebooks do:
```
source setup.sh
jupyter notebook --no-browser
```
and then on your local machine
```
ssh -N -f -L localhost:8888:localhost:8888 daniel@strange.bu.edu
```
with your username, using the ports as given by the jupyter server.

## Using docker

Setup the docker container with pre-built ipbus:

``` shell
docker run -it --name tamalero danbarto/ubuntu20.04-uhal-python38-tamalero:latest /bin/bash
```

Inside docker, check out this repository and install any missing / updated python packages:

``` shell
git clone https://gitlab.cern.ch/cms-etl-electronics/module_test_sw.git
pip install --editable .
pip install ipython
```

Setup the paths using `source setup.sh` inside the `module_test_sw` directory and check that ipbus is actually working with `python3 -i -c "import uhal"`.

This docker image is not updated weekly so some python dependencies might be missing.
Please install those via pip.

Below is an example for setting up a RB using docker.
We first need to start control hub (only needed to be done once), set up all the paths and run test_tamalero in power-up mode.
``` shell
/opt/cactus/bin/controlhub_start
cd module_test_sw
source setup.sh
ipython -i test_tamalero.py -- --control_hub --kcu 192.168.0.10 --verbose --configuration modulev0 --power_up
```


## Useful block diagrams for connectivity and data flow

[RB v1.6 schematic](http://physics.bu.edu/~wusx/download/ETL_RB/v1.6/ETL_RB_V1.6.PDF)

![module connectivity](docs/module-connectivity.pdf)

## References

[BU EDF](http://ohm.bu.edu/trac/edf/wiki/CMSMipTiming)

### GBT-SCA

[The GBT-SCA, a radiation tolerant ASIC for detector control and monitoring applications in HEP experiments](https://cds.cern.ch/record/2158969?ln=de)

[User Manual](https://espace.cern.ch/GBT-Project/GBT-SCA/Manuals/GBT-SCA_Manual_2019.002.pdf)

### lpGBT

[Specifications](https://espace.cern.ch/GBT-Project/LpGBT/Specifications/LpGbtxSpecifications.pdf)

[Testing presentation](https://espace.cern.ch/GBT-Project/LpGBT/Presentations/20190118lpGBTnews.pdf)

[User Manual](https://lpgbt.web.cern.ch/lpgbt/v0/)

### KCU105

[Xilinx](https://www.xilinx.com/products/boards-and-kits/kcu105.html)

A simple helper script to configure the KCU105 is available in `kcu_clock_config`. It can be run as:

``` bash
python3 configure_kcu_clock_synth.py
```

It will prompt you to specify the number of the serial port (e.g. `2` for
`/dev/ttyUSB2`), and will give some suggestions about which port it likely is.
If you only have one KCU105 connected to the UART then it is likely the first
choice.

Confirm `y` and it will automatically configure the KCU105.
