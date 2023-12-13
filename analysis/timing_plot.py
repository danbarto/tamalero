#!/usr/bin/env python3
import json
import awkward as ak
import argparse
import numpy as np
import hist
import os
import matplotlib.pyplot as plt
import mplhep as hep
plt.style.use(hep.style.CMS)

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--input', action='store', default='output_qinj_10fC', help="Binary file to read from")
    args = argParser.parse_args()

    # with open(f"../output/{args.input}.json", "r") as f:
    with open(f"../ETROC_output/{args.input}.json", "r") as f:
        res = json.load(f)
    events = ak.from_json(res)

    plot_dir = f"../results/{args.input.replace('.','p')}"

    if not os.path.isdir(plot_dir):
        os.makedirs(plot_dir)

    events['bin'] = 3.125 / events.cal_code
    events['toa'] = 12.5 - events.bin * events.toa_code
    events['tot'] = (2*events.tot_code - np.floor(events.tot_code/32))*events.bin

    toa = np.nan_to_num(ak.flatten(events.toa), nan=0, posinf=0, neginf=0)
    toa = toa[((toa>7)&(toa<9))]
    toa_mean = np.mean(toa)

    time_axis = hist.axis.Regular(100, toa_mean-2, toa_mean+2, name="time", label="time")
    time_axis_ext = hist.axis.Regular(100, 0, 15, name="time", label="time")
    cal_axis = hist.axis.Regular(2**10, 0, 2**10, name="cal", label="cal")
    #nhits_axis = hist.axis.Regular(257, -0.5, 256.5, name='n', label=r"$N_{hits}$")
    nhits_axis = hist.axis.Regular(6, -0.5, 5.5, name='n', label=r"$N_{hits}$")
    pixel_axis = hist.axis.StrCategory([], name="pixel", label="Pixel", growth=True)

    toa_hist = hist.Hist(time_axis_ext)
    toa_hist_perf = hist.Hist(time_axis_ext, pixel_axis)
    tot_hist = hist.Hist(time_axis_ext)
    tot_hist_perf = hist.Hist(time_axis_ext, pixel_axis)
    cal_hist = hist.Hist(cal_axis)
    cal_hist_perf = hist.Hist(cal_axis, pixel_axis)
    toa_code_hist = hist.Hist(cal_axis)
    nhits_hist = hist.Hist(nhits_axis)

    # Making number of hits plot
    nhits_hist.fill(n=events.nhits)

    fig, ax = plt.subplots()
    nhits_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'{plot_dir}/nhits.png')


    # Making CAL plot
    cal_hist.fill(cal=ak.flatten(events.cal_code))

    fig, ax = plt.subplots()
    cal_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'{plot_dir}/cal_code.png')

    # Making TOA plots

    toa_code_hist.fill(cal=ak.flatten(events.toa_code))

    fig, ax = plt.subplots()
    toa_code_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'{plot_dir}/toa_code.png')


    toa_hist.fill(time=ak.flatten(events.toa))

    fig, ax = plt.subplots()
    toa_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'{plot_dir}/toa.png')

    tot_hist.fill(time=ak.flatten(events.tot))

    fig, ax = plt.subplots()
    tot_hist.plot1d(
        ax=ax,
    )
    ax.set_xlabel("Time over threshold (ns)")
    ax.set_ylabel("Events")
    fig.savefig(f'{plot_dir}/tot.png')

    tot_hist_perf.fill(
        pixel="(15,0)",
        time=ak.flatten(events.tot[((events.nhits==4)&(events.row==15)&(events.col==0))]),
    )
    tot_hist_perf.fill(
        pixel="(15,1)",
        time=ak.flatten(events.tot[((events.nhits==4)&(events.row==15)&(events.col==1))]),
    )
    tot_hist_perf.fill(
        pixel="(15,2)",
        time=ak.flatten(events.tot[((events.nhits==4)&(events.row==15)&(events.col==2))]),
    )
    tot_hist_perf.fill(
        pixel="(15,3)",
        time=ak.flatten(events.tot[((events.nhits==4)&(events.row==15)&(events.col==3))]),
    )

    fig, ax = plt.subplots()
    tot_hist_perf.plot1d(
         ax=ax,
    )
    ax.set_xlabel("Time over threshold (ns)")
    ax.set_ylabel("Events")
    plt.legend(loc=0)
    fig.savefig(f'{plot_dir}/tot_comparison.png')


    tot_mean = ak.mean(events.tot[((events.nhits==4)&(events.row==15)&(events.col==1))])
    print(f"TOT mean for best pixel: {tot_mean}")


    cal_hist_perf.fill(
        pixel="(15,0)",
        cal=ak.flatten(events.cal_code[((events.nhits==4)&(events.row==15)&(events.col==0))]),
    )
    cal_hist_perf.fill(
        pixel="(15,1)",
        cal=ak.flatten(events.cal_code[((events.nhits==4)&(events.row==15)&(events.col==1))]),
    )
    cal_hist_perf.fill(
        pixel="(15,2)",
        cal=ak.flatten(events.cal_code[((events.nhits==4)&(events.row==15)&(events.col==2))]),
    )
    cal_hist_perf.fill(
        pixel="(15,3)",
        cal=ak.flatten(events.cal_code[((events.nhits==4)&(events.row==15)&(events.col==3))]),
    )

    fig, ax = plt.subplots()
    cal_hist_perf[180j:220j:1j,::].plot1d(
        ax=ax,
    )
    ax.set_xlabel("Cal code")
    ax.set_ylabel("Events")
    plt.legend(loc=0)
    fig.savefig(f'{plot_dir}/cal_comparison.png')


    ### TOA performance (?)
    ###
    '''
    toa_hist_perf.fill(
        pixel="(15,0)",
        time=ak.flatten(events.toa[((events.nhits==4)&(events.row==15)&(events.col==0))]),
    )
    toa_hist_perf.fill(
        pixel="(15,1)",
        time=ak.flatten(events.toa[((events.nhits==4)&(events.row==15)&(events.col==1))]),
    )
    toa_hist_perf.fill(
        pixel="(15,2)",
        time=ak.flatten(events.toa[((events.nhits==4)&(events.row==15)&(events.col==2))]),
    )
    toa_hist_perf.fill(
        pixel="(15,3)",
        time=ak.flatten(events.toa[((events.nhits==4)&(events.row==15)&(events.col==3))]),
    )

    # print(f"Mean TOT of pixel row: {15}, col: {0} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==0))])}")
    # print(f"Mean TOT of pixel row: {15}, col: {1} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==1))])}")
    # print(f"Mean TOT of pixel row: {15}, col: {2} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==2))])}")
    # print(f"Mean TOT of pixel row: {15}, col: {3} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==3))])} \n")
    tot_0 = events.tot[((events.nhits==4)&(events.row==15)&(events.col==0))]
    tot_1 = events.tot[((events.nhits==4)&(events.row==15)&(events.col==1))]
    tot_2 = events.tot[((events.nhits==4)&(events.row==15)&(events.col==2))]
    tot_3 = events.tot[((events.nhits==4)&(events.row==15)&(events.col==3))]
    '''
    # Number of hits = 3
    toa_hist_perf.fill(
        pixel="(15,0)",
        time=ak.flatten(events.toa[((events.nhits==3)&(events.row==15)&(events.col==0))]),
    )
    toa_hist_perf.fill(
        pixel="(15,1)",
        time=ak.flatten(events.toa[((events.nhits==3)&(events.row==15)&(events.col==1))]),
    )
    toa_hist_perf.fill(
        pixel="(15,2)",
        time=ak.flatten(events.toa[((events.nhits==3)&(events.row==15)&(events.col==2))]),
    )
    toa_hist_perf.fill(
        pixel="(15,3)",
        time=ak.flatten(events.toa[((events.nhits==3)&(events.row==15)&(events.col==3))]),
    )

    # print(f"Mean TOT of pixel row: {15}, col: {0} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==0))])}")
    # print(f"Mean TOT of pixel row: {15}, col: {1} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==1))])}")
    # print(f"Mean TOT of pixel row: {15}, col: {2} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==2))])}")
    # print(f"Mean TOT of pixel row: {15}, col: {3} is {np.mean(events.toa[((events.nhits==4)&(events.row==15)&(events.col==3))])} \n")
    tot_0 = events.tot[((events.nhits==3)&(events.row==15)&(events.col==0))]
    tot_1 = events.tot[((events.nhits==3)&(events.row==15)&(events.col==1))]
    tot_2 = events.tot[((events.nhits==3)&(events.row==15)&(events.col==2))]
    tot_3 = events.tot[((events.nhits==3)&(events.row==15)&(events.col==3))]
    tot_0 = tot_0[tot_0 < 100000]
    tot_1 = tot_1[tot_1 < 100000]
    tot_2 = tot_2[tot_2 < 100000]
    tot_3 = tot_3[tot_3 < 100000]
    print(np.mean(tot_0))
    print(np.mean(tot_1))
    print(np.mean(tot_2))
    print(np.mean(tot_3))
    print(len(tot_0))
    print(np.std(tot_0) / len(tot_0))
    print(np.std(tot_1) / len(tot_1))
    print(np.std(tot_2) / len(tot_2))
    print(np.std(tot_3) / len(tot_3))

    print(events.tot[((events.nhits==3)&(events.row==15)&(events.col==3))])

    fig, ax = plt.subplots()
    toa_hist_perf[::2j,::].plot1d(
        ax=ax,
    )
    ax.set_xlabel("Time of arrival (ns)")
    ax.set_ylabel("Events")
    plt.legend(loc=0)
    fig.savefig(f'{plot_dir}/toa_comparison.png')



    # there are some nasty outliers that we remove
    # more studies are needed to understand them
    pix_selector = ((events.row==0)&(events.col==0)&(events.cal_code>150)&(events.cal_code<210))
    cal_code_0_0 = events.cal_code[pix_selector]
    bin_0_0 = 3.125/cal_code_0_0
    bin_0_0_avg = np.mean(ak.flatten(bin_0_0))
    toa_0_0 = 12.5 - bin_0_0 * events.toa_code[pix_selector]
    toa_0_0 = toa_0_0[((toa_0_0>7) & (toa_0_0<9))]

    toa_0_0_avg = 12.5 - bin_0_0_avg * events.toa_code[pix_selector]
    toa_0_0_avg = toa_0_0_avg[((toa_0_0_avg>7) & (toa_0_0_avg<9))]

    toa_0_0_mean = np.mean(toa_0_0)
    toa_0_0_std = np.std(toa_0_0)

    toa_0_0_avg_mean = np.mean(toa_0_0_avg)
    toa_0_0_avg_std = np.std(toa_0_0_avg)

    print(f"Found mean time of {round(toa_0_0_avg_mean,3)}fs, with std dev of {round(toa_0_0_avg_std*1000, 0)}ps")

    toa_hist = hist.Hist(time_axis)
    toa_hist.fill(time=ak.flatten(events.toa[((events.row==0)&(events.col==0))]))

    fig, ax = plt.subplots()
    toa_hist.plot1d(
        ax=ax,
    )

    fig.savefig(f'{plot_dir}/toa_0_0.png')
