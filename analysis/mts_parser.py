import numpy as np
import json
import argparse
import matplotlib.pyplot as plt
import os

def toPixNum(row, col, w):
    return col*w+row

def fromPixNum(pix, w):
    row = pix%w
    col = int(np.floor(pix/w))
    return row, col

argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--filepath', '-f',  action='store', help="path to file")
argParser.add_argument('--module', '-m',  action='store', help="path to file")
argParser.add_argument('--timestamp', '-t',  action='store', help="timestamp")
argParser.add_argument('--pix_hists',  action='store_true', help="1d hists for each pixel")

args = argParser.parse_args()


if args.filepath:
   with open(args.filepath, 'r') as f:
       data = json.load(f)
   names = args.filepath.split('/')
   args.module = names[1]
   args.timestamp = names[2]
   if '/manual_thresh_scan_data.json' in args.filpath:
       outpath = args.filpath.split('/manual_thresh_scan_data.json')[0]
   else:
       outpath = args.filpath.split('/thresh_scan_data.json')[0]
   print('Found file at ' + args.filepath)
elif args.module and args.timestamp:
    try:
        with open(f'outputs/{args.module}/{args.timestamp}/manual_thresh_scan_data.json', 'r') as f:
            data = json.load(f)
        outpath = f'outputs/{args.module}/{args.timestamp}/'
    except:
        with open(f'outputs/{args.module}/{args.timestamp}/thresh_scan_data.json', 'r') as f:
            data = json.load(f)
        outpath = f'outputs/{args.module}/{args.timestamp}/'
else:
    print('Insufficient info to load data.')
    adsfasdfadf

vth_axis    = np.array([float(v) for v in data])
hit_rate    = np.array([data[v] for v in data], dtype = float).T
N_pix       = len(hit_rate) # total # of pixels
N_pix_w     = int(round(np.sqrt(N_pix))) # N_pix in NxN layout
max_indices = np.argmax(hit_rate, axis=1)
maximums    = vth_axis[max_indices]
max_matrix  = np.empty([N_pix_w, N_pix_w])
noise_matrix  = np.empty([N_pix_w, N_pix_w])
threshold_matrix = np.empty([N_pix_w, N_pix_w])

for pix in range(N_pix):
    r, c = fromPixNum(pix, N_pix_w)
    max_matrix[r][c] = maximums[pix]
    noise_matrix[r][c] = np.size(np.nonzero(hit_rate[pix]))
    max_value = vth_axis[hit_rate[pix]==max(hit_rate[pix])]
    if isinstance(max_value, np.ndarray):
        max_value = max_value[-1]
    zero_dac_values = vth_axis[((vth_axis>(max_value)) & (hit_rate[pix]==0))]
    if len(zero_dac_values)>0:
        threshold_matrix[r][c] = zero_dac_values[0] + 2
    else:
        threshold_matrix[r][c] = dac_max + 2
    if args.pix_hists:
        fig = plt.figure(figsize = (9, 7))
        pixdat = hit_rate[pix, :]
        width = 25
        idxlim = [np.min([0, np.argmin(pixdat - width)]), np.max([len(pixdat), np.argmax(pixdat + width)])]
        x = vth_axis[idxlim[0]:idxlim[1]]
        y = pixdat[idxlim[0]:idxlim[1]]
        plt.plot(x, y, '-o')
        plt.title(f'Row {r} Col {c} Manual Threshold Scan\n3200 L1As, Module {args.module}')
        if not os.path.exists(outpath + '/mts_individual_pixels'):
            os.mkdir(outpath + '/mts_individual_pixels')
        plt.savefig(outpath + '/mts_individual_pixels/' + f'r{r}c{c}_mts_results.png')
        if r == 15 and c == 0:
            print(r, c)
            plt.show()
        plt.close()
# 2D histogram of the mean
# this is based on the code for automatic sigmoid fits
# for software emulator data below
fig, ax = plt.subplots(2,1, figsize=(15,15))
ax[0].set_title("Peak values of threshold scan")
ax[1].set_title("Noise width of threshold scan")
cax1 = ax[0].matshow(max_matrix)
cax2 = ax[1].matshow(noise_matrix)
fig.colorbar(cax1,ax=ax[0])
fig.colorbar(cax2,ax=ax[1])

ax[0].set_xticks(np.arange(N_pix_w))
ax[0].set_yticks(np.arange(N_pix_w))

ax[1].set_xticks(np.arange(N_pix_w))
ax[1].set_yticks(np.arange(N_pix_w))

for i in range(N_pix_w):
    for j in range(N_pix_w):
        text = ax[0].text(j, i, int(max_matrix[i,j]),
                ha="center", va="center", color="w", fontsize="xx-small")

        text1 = ax[1].text(j, i, int(noise_matrix[i,j]),
                ha="center", va="center", color="w", fontsize="xx-small")

#fig.savefig(f'{result_dir}/peak_and_noiseWidth_thresholds.png')
plt.show()

plt.close(fig)



