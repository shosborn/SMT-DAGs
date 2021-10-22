#/usr/bin/python3
# Make sure to run this as root!!!!!
import os
import sys
import re
import csv
import time
import subprocess


# Single tasks:
# 0, binary_name, task_name, iterations, my_core, runID, save?, period, criticality, phase
# Paired tasks:
# 1, binary_name, task_name, iterations, my_core, runID, save?, period, criticality, phase, other_binary_name, other_task_name


binary_path = "./SD-VBS/dag_binaries/"
stderr_file = open("./deadline_misses", 'w+')

BINARY_NAME = 1
TASK_NAME = 2
NUM_ITERS = 3
CORE_NUM = 4
RUN_ID = 5
SAVE_RESULT = 6
PERIOD = 7
CRT_LEVEL = 8
PHASE= 9

OTHER_BINARY_NAME = 10
OTHER_TASK_NAME = 11
# OTHER_CORE_NUM = 12
# PAIR_ID = 12

all_pids=[]
def run(command):
    print(command)
    os.system(command)

def addpid(pid):
    with open("./pids.txt", "a") as f:
        f.write(str(pid) + "\n")
def ID2PID(lookupID):
    res = None
    # Find benchmark PID (avoid getting shell or numactl PID)
    try:
        res = subprocess.check_output("pgrep -af '" + lookupID + "' | grep -v numactl", shell=True)
    except:
        res = None
    if res:
        # Ignore the newline
        return res.decode("utf-8").split(" ")[0].strip()
    else:
        return None

def main(pathName):
    with open("./pids.txt", "w") as f:
        f.write("")
   
    input_cmd = {}
    # Load input command for each binary
    
    with open("SD-VBS/sd-vbsNames.txt") as f:
        for line in f:
            name, cmd = line.split(maxsplit=1)
            input_cmd[name.replace("./", "")] = cmd.replace("./", "./SD-VBS/").strip()

    task_launches = []
    max_core = 0
    all_cores = set()
    # Load task specifications
    with open(pathName, "r") as file:
        for line in file:
            parameters = line.split(",")
            task_launches.append(parameters)
            core_num = int(parameters[CORE_NUM]) % 16
            # if max_core < core_num:
            #     max_core = core_num
            all_cores.add(core_num)
            # if parameters[0] == '1':
            #     other_core_num = int(parameters[OTHER_CORE_NUM]) % 16
            #     if other_core_num > max_core:
            #         max_core = other_core_num

    core_count = max_core+1
    # print(parameters)

    ### Allocate Cache Ways ###
    run('mount -t resctrl resctrl /sys/fs/resctrl') 
    run('sudo echo "L3:0=0000;1=0000;2=0000;3=000f" | sudo tee /sys/fs/resctrl/schemata')
    for core in range(16):
        if core not in all_cores:
            continue
        run("mkdir -p /sys/fs/resctrl/core-{}".format(core))
        ccx = core // 4
        in_ccx = core % 4
        mask = "0000"
        mask = mask[:in_ccx] +'f'+ mask[in_ccx+1:]
        if ccx == 0:
            run('echo "L3:0=' + mask + ';1=0000;2=0000;3=0000" > /sys/fs/resctrl/core-{}/schemata'.format(core))
        if ccx == 1:
            run('echo "L3:0=0000;1='  + mask + ';2=0000;3=0000" > /sys/fs/resctrl/core-{}/schemata'.format(core))
        if ccx == 2:
            run('echo "L3:0=0000;1=0000;2='+ mask +';3=0000" > /sys/fs/resctrl/core-{}/schemata'.format(core))
        if ccx == 3:
            run('echo "L3:0=0000;1=0000;2=0000;3=' + mask + '" > /sys/fs/resctrl/core-{}/schemata'.format(core))

    # return 1
    run("rm -rf /dev/shm/*")


    pairID = 0
    ### Dispatch tasks
    for launch in task_launches:
        binary_name = launch[BINARY_NAME].strip()
        task_name = launch[TASK_NAME].strip()
        num_iters = launch[NUM_ITERS].strip()
        core_num =launch[CORE_NUM].strip()
        run_id = launch[RUN_ID].strip()
        save_result = launch[SAVE_RESULT].strip()
        period = launch[PERIOD].strip()
        crt_level = launch[CRT_LEVEL].strip()
        phase = launch[PHASE].strip()


        phys_core = int(core_num) % 16
        if ID2PID(task_name):
            print("ERROR: Task Name {} is already running! Did you end the previous case study?".format(task_name))
            return 1
        # single tasks
        if launch[0] == '0':
            binary =  binary_path + binary_name + "_single"
            # Arg format: <unique name> <num_iters> <core> <NULL runID> <save?> <period> <crit lvl>
            arg = " " + task_name  + " " + num_iters +" " +  core_num +" " +  run_id +" " + save_result+" " + period +" " +  crt_level + " "+ phase
            # print(input_cmd[binary_name] + " | numactl --interleave=all " + binary + arg)
            bench_tsk = subprocess.Popen(input_cmd[binary_name] + " | numactl --interleave=all " + binary + arg, shell=True, executable='/bin/bash', stderr=stderr_file)
            pid_str = ID2PID(binary + " " + task_name)
            if not pid_str:
                print("Unable to launch {} as a solo task! Exiting...".format(task_name))
                return 1
            run("echo " + pid_str + " > /sys/fs/resctrl/core-" + str(phys_core) + "/tasks")
        else:
            # Paried tasks
            other_binary_name = launch[OTHER_BINARY_NAME].strip()
            other_task_name = launch[OTHER_TASK_NAME].strip()
            other_core_num = str(int(core_num)+16)

            #Check if SMT-paired correctly
            # assert(abs(int(core_num)-int(other_core_num)) == 16)
            if ID2PID(other_task_name):
                print("ERROR: Task Name {} is already running! Did you end the previous case study?".format(other_task_name))
                return 1
            binary =  binary_path + binary_name + "_pair"
            other_binary =  binary_path + other_binary_name + "_pair"
            # Arg format: <unique name> <num iters> <core> <0 other core> <other name> <runID> <save?> <pairID> <period> <crit lvl>
            arg1 = " " + task_name  + " " + num_iters +" " +  core_num +" " + other_core_num+" "+ other_task_name+" "+ run_id +" " + save_result+" " +str(pairID) +" "+ period +" " +  crt_level +" "+phase
            arg2 = " " + other_task_name  + " " + num_iters +" " +  other_core_num +" " + core_num+" "+ task_name+" "+ run_id +" " + save_result+" " +str(pairID) +" "+ period +" " +  crt_level+" " +phase
            # print(input_cmd[binary_name] + " | numactl --membind=0 " + binary + arg1)
            # print(input_cmd[other_binary_name] + " | numactl --membind=1 " + other_binary + arg2)
            bench_tsk1 = subprocess.Popen(input_cmd[binary_name] + " | numactl --membind=0 " + binary + arg1, shell=True, executable='/bin/bash', stderr=stderr_file)
            bench_tsk2 = subprocess.Popen(input_cmd[other_binary_name] + " | numactl --membind=1 " + other_binary + arg2, shell=True, executable='/bin/bash', stderr=stderr_file)
            # print(binary + " " + task_name,other_binary + " " +other_task_name)
            pid1_str = ID2PID(binary + " " + task_name)
            pid2_str = ID2PID(other_binary + " " +other_task_name)
            if not pid1_str or not pid2_str:
                print("Unable to launch {} and {} in a pair! Exiting...".format(task_name, other_task_name))
                return 1
            
            run("echo " + pid1_str + " > /sys/fs/resctrl/core-" + str(phys_core) + "/tasks")
            run("echo " + pid2_str + " > /sys/fs/resctrl/core-" + str(phys_core) + "/tasks")
            pairID += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <task sets path>")
        exit(1)
    if os.geteuid() != 0:
        print("You must run this script as root to enable cache isolation and access LITMUS-RT.")
        exit(1)
    pathName = sys.argv[1]
    err = main(pathName)
    input("Done. Waiting for termination signal...")
    exit(err)


