next_file_index="/home/daq/ETROC2_Test_Stand/ScopeHandler/Lecroy/Acquisition/next_run_number.txt"
index=`cat $next_file_index`
echo $index
ipython3 fnal_laser_test.py -- --kcu 192.168.0.10 --hard_reset
python3 daq.py --run_time 100 --n_events $1 --l1a_rate 0 --ext_l1a --kcu 192.168.0.10 --run $index
python3 root_dumper.py --input $index