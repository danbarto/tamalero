import math
import numpy as np
from time import sleep
from yaml import load, dump
import os

from tamalero.KCU import KCU

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def get_temp(v_out, v_ref, r_ref, t_1, r_1, b, celcius=True):
    """
    Calculate the temperature of a thermistor, given the voltage measured on it.

    Arguments:
    v_out (float) -- voltage measured on the thermistor
    v_ref (float) -- reference voltage
    r_ref (float) -- volatge divider resistor
    t_1 (float) -- reference temperature of thermistor
    r_1 (float) -- resistance of NTC at reference temperature
    b (float) -- B coefficient, with B = (ln(r_1)-ln(r_t)) / (1/t_1 - 1/t_out)

    Keyword arguments:
    celcius (bool) -- give and return the temperature in degree celcius. Kelvin scale used otherwise.
    """

    delta_t = 273.15 if celcius else 0
    try:
        r_t = r_ref / (v_ref/v_out - 1)
        t_2 = b/((b/(t_1+delta_t)) - math.log(r_1) + math.log(r_t))
    except ZeroDivisionError:
        print ("Temperature calculation failed!")
        return -999
    return t_2-delta_t


def read_mapping(f_in, selection='adc', flavor='small'):
    flavors = {'small':0, 'medium':1, 'large': 2}
    i_flavor = flavors[flavor]
    with open(f_in) as f:
        mapping = load(f, Loader=Loader)[selection]
    return {v:mapping[v] for v in mapping.keys() if flavors[mapping[v]['flavor']] <= flavors[flavor]}

def dump_alignment_to_file(rb, f_out):
    res = rb.dump_uplink_alignment()
    with open(f_out, 'w') as f:
        dump(res, f, Dumper=Dumper)

def load_alignment_from_file(f_in):
    with open(f_in, 'r') as f:
        res = load(f, Loader=Loader)
    return res

def load_yaml(f_in):
    with open(f_in, 'r') as f:
        res = load(f, Loader=Loader)
    return res

def prbs_phase_scan(lpgbt, f_out='phase_scan.txt'):
    with open(f_out, "w") as f:
        for phase in range(0x0, 0x1ff, 1):
            phase_ns = (50.0*(phase&0xf) + 800.0*(phase>>4))/1000
            lpgbt.set_ps0_phase(phase)
            lpgbt.reset_pattern_checkers()
            sleep(0.5)
            #read_pattern_checkers()
            prbs_errs = lpgbt.read_pattern_checkers(quiet=True)[0]
            s = ("{} "*(len(prbs_errs)+1)).format(*([phase_ns]+prbs_errs))
            f.write("%s\n" % s)
            print (s)


def plot_phase_scan(f_in, channel):
    import matplotlib.pyplot as plt
    data = np.loadtxt(f_in)
    plt.yscale("log")
    plt.plot(data[:,0], data[:,channel])
    plt.show()


def header():
    from tamalero.colors import magenta
    try:
        print(magenta("\n\n\
        ████████╗ █████╗ ███╗   ███╗ █████╗ ██╗     ███████╗███████╗\n\
        ╚══██╔══╝██╔══██╗████╗ ████║██╔══██╗██║     ██╔════╝██╔════╝\n\
           ██║   ███████║██╔████╔██║███████║██║     █████╗  ███████╗\n\
           ██║   ██╔══██║██║╚██╔╝██║██╔══██║██║     ██╔══╝  ╚════██║\n\
           ██║   ██║  ██║██║ ╚═╝ ██║██║  ██║███████╗███████╗███████║\n\
           ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝\n\n\
        "))
    except UnicodeEncodeError:
        print (magenta("\n\n\
        #########################\n\
        #######  TAMALES  #######\n\
        #########################\n\n\
        "))


def make_version_header(res):
    from tamalero.colors import blue
    print ("\n ### Testing ETL Readout Board: ###")
    print (blue("- Version: %s.%s"%(res["rb_ver_major"], res["rb_ver_minor"])))
    print (blue("- Flavor: %s"%res["rb_flavor"]))
    print (blue("- Serial number: %s"%res["serial_number"]))
    print (blue("- lpGBT version: %s"%res["lpgbt_ver"]))
    print (blue("- lpGBT serial number: %s"%res['lpgbt_serial']))
    print (blue("- Trigger lpGBT mounted: %s"%res['trigger']))
    print ("")


def chunk(in_list, n):
    return [in_list[i * n:(i + 1) * n] for i in range((len(in_list) + n - 1) // n )] 

def download_address_table(version):
    import os
    import requests
    import json
    import urllib.parse


    r2 = requests.get(f"https://gitlab.cern.ch/api/v4/projects/107856/repository/commits?ref=devel")
    log = json.loads(r2.content)
    last_commit_sha = log[0]['id'][:7]

    r = requests.get(f"https://gitlab.cern.ch/api/v4/projects/107856/repository/tree?ref={version}&&path=address_tables&&recursive=True")
    tree = json.loads(r.content)
    if isinstance(tree, list):
        print ("Successfully got list of address table files from gitlab.")
    else:
        version = last_commit_sha
        if os.path.isdir(f'address_table/{version}/'):
            # already downloaded.
            return version
        r = requests.get(f"https://gitlab.cern.ch/api/v4/projects/107856/repository/tree?ref=devel&&path=address_tables&&recursive=True")
        tree = json.loads(r.content)
        print (f"Local firmware version detected. Will download address table corresponding to commit {version}.")

    
    os.makedirs(f"address_table/{version}")
    for f in tree:
        if f['type'] == 'tree':
            os.makedirs(f"address_table/{version}/{f['name']}")
        elif f['type'] == 'blob':
            # needs URL encode: https://www.w3schools.com/tags/ref_urlencode.ASP
            path = urllib.parse.quote_plus(f['path']).replace('.', '%2E')  # python thinks . is fine, so we replace it manually
            res = requests.get(f"https://gitlab.cern.ch/api/v4/projects/107856/repository/files/{path}/raw?ref={version}")
            local_path = f['path'].replace('address_tables/', '')
            open(f"address_table/{version}/{local_path}", 'wb').write(res.content)

    return version

def check_repo_status(kcu_version=None):
    import requests
    import json
    import os
    from git import Repo
    from tamalero.colors import red, green

    # get remote repo log
    r = requests.get(f"https://gitlab.cern.ch/api/v4/projects/110883/repository/commits")
    log = json.loads(r.content)
    last_commit_sha = log[0]['id']

    # get local log
    working_tree_dir = os.path.expandvars("$TAMALERO_BASE")
    repo = Repo(working_tree_dir)
    hashes = [ c.hexsha for c in repo.iter_commits(max_count=50) ]
    tags = [ t.name.strip('v') for t in repo.tags ]

    #
    commit_based = (last_commit_sha in hashes)
    tag_based = kcu_version in tags if kcu_version is not None else True

    if commit_based and tag_based:
        print (green("Your tamalero repository is up-to-date with master"))
    else:
        print (red("\n! WARNING: You are potentially working on an outdated or out-of-sync version of tamalero !"))
        if not tag_based:
            print (red(f"You are using KCU firmware version {kcu_version}, but the corresponding tag has not been found in your local tamalero repo."))
            print (red(f"You can ignore this warning for firmware versions BEFORE 1.3.5\n"))
        else:
            print (red("Please pull a more recent version from gitlab.\n"))

def get_kcu(kcu_address, control_hub=True, host='localhost', verbose=False):
    # Get the current firmware version number
    if verbose:
        if control_hub:
            print(f"Using control hub on {host=}, {kcu_address=}")
        else:
            print(f"NOT using control hub on {host=}, {kcu_address=}")

    import uhal
    if control_hub:
        ipb_path = f"chtcp-2.0://{host}:10203?target={kcu_address}:50001"
    else:
        ipb_path = f"ipbusudp-2.0://{kcu_address}:50001"
    print (f"IPBus address: {ipb_path}")

    try:
        kcu_tmp = KCU(name="tmp_kcu",
                    ipb_path=ipb_path,
                    adr_table="address_table/generic/etl_test_fw.xml")
    except uhal.exception:
        print ("Could not establish connection with KCU. Exiting.")
        return 0

        #raise
    xml_sha     = kcu_tmp.get_xml_sha()
    if verbose:
        print (f"Address table hash: {xml_sha}")

    if not os.path.isdir(f"address_table/{xml_sha}"):
        print ("Downloading latest firmware version address table.")
        xml_sha = download_address_table(xml_sha)

    kcu = KCU(name="my_device",
              ipb_path=ipb_path,
              adr_table=f"address_table/{xml_sha}/etl_test_fw.xml")

    kcu.get_firmware_version(string=False)

    return kcu

if __name__ == '__main__':
    print ("Temperature example:")
    print (get_temp(0.8159, 1.5, 10000, 25, 10000, 3900))
