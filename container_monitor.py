#!/usr/bin/python
# This code reads BPF maps that have TCP, HTTP and disk read/write data
#    for all containers provided in the command line.
# Maps data is subsequently written to a log file---one logfile per container.

from __future__ import print_function
from bcc import BPF
from pyroute2 import IPRoute, IPDB
from ctypes import c_uint,c_int, c_ulong
import socket
import time
import subprocess
import struct
import traceback
import pdb
import os
import argparse

# labels of the bins used to store the histogram.
hist_bins = [];
for i in range(0,64):
    hist_bins.append(str(2**i) +' -> ' + str((2**(i+1)) - 1) + ' : ' )

# This function writes the CPU/HTTP stats table to the logfile.
def write_hist_to_file(logfile, dist_array,title):
    dist_temp = list(dist_array);
    for i in reversed(range(0,64)):
        if dist_temp[i] == 0:
            del(dist_temp[i])
        else:
            break
    idx = 0
    print("---------------")
    if len(dist_temp) > 0:
        logfile.write(title + '\n')
        for val in dist_temp:
            logfile.write(hist_bins[idx] + '%s' % val + '\n')
            print(hist_bins[idx] + '%s' % val)
            idx+=1

# Writing the current time to the logfile
def write_time_to_log(logfile):
    logfile.write('---------------------------------------------------\n')
    logfile.write('time=%s:\n' % time.time())
    logfile.write('time=%s:\n' % time.strftime("%H:%M:%S - %d/%m/%Y"))

def get_lxc_info(lxc_name):
    info_cmd = [ 'bash', '-c', 'lxc-info --name ' + lxc_name ]
    cmd_output = subprocess.check_output(info_cmd).split('\n')
    pid = filter(bool, cmd_output[2].split(' '))[1]
    veth = filter(bool, cmd_output[8].split(' '))[1]
    return {'pid':pid, 'veth':veth}

# main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("container_name", help="Name of the container to monitor.")
    parser.add_argument("-i", help="interval between each poll (default 30 seconds).", type=int)
    parser.add_argument("-o", help="output file to store logs(default is <container_name>.log.")
    args = parser.parse_args()
    container_details = get_lxc_info(args.container_name)
    log_interval = 30
    if args.i:
        log_interval = args.i;

    logfile_name = args.container_name + '.log'
    if args.o:
        logfile_name = args.o

    logfile = open(logfile_name, 'a', 0)
    with open('get_cpu_info.c_TEMPLATE', 'r') as content_file:
        bpf_text = content_file.read()

    bpf_text = bpf_text.replace('CONTAINER_PARENT_PID', '%d' % int(container_details['pid']))
    bpf_cpu_t = BPF(text=bpf_text)

    bpf_cpu_t.attach_kprobe(event="finish_task_switch", fn_name="sched_switch")

    # empty bins to receive the data collected
    cpu_dist_array = [0] * 64
    try:
        while (1):
            # 30 second time interval between polling
            time.sleep(log_interval)
            write_time_to_log(logfile)
            cpudist = bpf_cpu_t["cpudist"]
        
            # The cpudist contains data for all PIDs we filter here only
            # the PIDs that belong to the required lxc
            for obj in cpudist:
                if obj.pid != 0:
                        cpu_dist_array[obj.slot] += cpudist[obj].value
            
            cpudist.clear()
            write_hist_to_file(logfile, cpu_dist_array,"usec:count");
            #reseting the bins and tables to zero
            cpu_dist_array = [0] * 64
    except Exception as e:
        traceback.print_exc()
    finally:
        logfile.close()


if __name__ == "__main__":
    main()
