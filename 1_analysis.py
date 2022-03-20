#!/usr/bin/python

# General libraries
import os, sys, time, json

# Probius libraries
import common
import testcase
import vnf_mgmt
import workload
import database

def load_global_configurations(conf_file):
    config = {}

    with open(conf_file) as data_file:
        data = json.load(data_file)

        config["inbound"] = data["interface"]["inbound"]
        config["outbound"] = data["interface"]["outbound"]

        config["cpu"] = data["resource"]["cpu"]
        config["mem"] = data["resource"]["mem"]

        config["sender"] = data["workload"]["sender"]
        config["run_sender"] = data["workload"]["run_sender"]
        config["stop_sender"] = data["workload"]["stop_sender"]

        config["receiver"] = data["workload"]["receiver"]
        config["run_receiver"] = data["workload"]["run_receiver"]
        config["stop_receiver"] = data["workload"]["stop_receiver"]

        config["local_receiver_ip"] = data["workload"]["local_receiver_ip"]
        config["local_receiver_nat_ip"] = data["workload"]["local_receiver_nat_ip"]

        config["monitor_time"] = data["workload"]["monitor_time"]
        config["trace_time"] = data["workload"]["trace_time"]

        config["sessions"] = data["workload"]["sessions"]
        config["protocol"] = data["workload"]["protocol"]
        config["bandwidth"] = data["workload"]["bandwidth"]

        config["measure_latency"] = data["workload"]["measure_latency"]

    return config

def run_analysis(g_config, config, case):
    # make the resources of VNFs
    cpus, mems = vnf_mgmt.make_resources_VNFs(g_config, config, case, common.local_resource_constraint)
    print ("1")

    for cpu in cpus:
        # get cpuset of VNFs
        cpuset = vnf_mgmt.get_cpuset_of_VNFs(cpu, case)
        print ("2")

        if common.debug == False:
            # set cpus of VNFs
            #vnf_mgmt.set_cpus_of_VNFs(cpu, cpuset, case)
            print ("3")

        for mem in mems:
            if common.debug == False:
                # set memories of VNFs
                #vnf_mgmt.set_mems_of_VNFs(mem, case)
                print ("4")

            #print ("###########################\n")
            #print (len(case))
            # print the info of the current testcase

            for idx in range(len(case)):
                print (case[idx], cpu[idx], mem[idx])
            
            if common.debug == False:
                #print("Here!")
                # send workload (run monitor and trace)
                
                workload.send_workloads(g_config, config, case, common.trace_state_transitions)
                print ("5")

runmode = ""
num_VNFs = 0
list_VNFs = ""

if len(sys.argv) == 2:
    runmode = sys.argv[1]
    if runmode != "vnf": # measure single VNF cases
        print ("%s { vnf | sc [# of VNFs] | case [list of VNFs(,)] }" % sys.argv[0])
        exit(0)
elif len(sys.argv) == 3:
    runmode = sys.argv[1]
    if runmode == "sc": # set the number of VNFs to chain
        num_VNFs = int(sys.argv[2])
    elif runmode == "case": # measure a specific service chain
        list_VNFs = sys.argv[2]
    else:
        print ("%s { vnf | sc [# of VNFs] | case [list of VNFs(,)] }" % sys.argv[0])
        exit(0)
else:
    print ("%s { vnf | sc [# of VNFs] | case [list of VNFs(,)] }" % sys.argv[0])
    exit(0)

# initialize database
database.initialize_database()
print ("Initialized the Probius database")

# load global configurations
g_config = load_global_configurations("config/global.conf")
print(g_config)
print ("Loaded global configurations")

# load VNF configurations
config = vnf_mgmt.load_VNF_configurations("config/vnf.conf")
print ("Loaded VNF configurations")
print(config)
#quit()

# get the list of VNFs
VNFs = vnf_mgmt.get_list_of_VNFs(config)
print ("Available VNFs in the config file: ", VNFs)

# load VNF chaining policies
policies = testcase.load_VNF_policies(VNFs, "config/policy.conf")
print ("Loaded VNF policies")

# shut down the active VNFs
#VNFs = vnf_mgmt.shut_down_VNFs(config, VNFs)
print ("Available VNFs in the hypervisor: ", VNFs)
start = time.time()

# analyze single VNFs only (ground truths)
if runmode == "vnf":
    cases = testcase.generate_testcase(VNFs)
    print ("Test cases: %d cases" % len(cases))

    for case in cases:
        print ("Current testcase: ", case)

        run_analysis(g_config, config, case)

    # update VNF statistics
    if common.debug == False:
        database.update_vnf_stats(config)
        print ("Updated VNF statistics")

# analyze all possible service chains with specific number of VNFs
elif runmode == "sc":
    all_cases = testcase.generate_testcases(VNFs)
    print ("All possible cases: %d cases" % len(all_cases))

    # filter out the chains against the policies
    cases = testcase.verify_testcases(VNFs, all_cases, policies)
    print ("Test cases: %d cases" % len(cases))

    for case in cases:
        if num_VNFs != 0 and len(case) != num_VNFs:
            continue

        print ("Current testcase: ", case)

        run_analysis(g_config, config, case)

    # update VNF statistics
    if common.debug == False:
        database.update_vnf_stats(config)
        print ("Updated VNF statistics")

# analyze a specific service chain
elif runmode == "case":
    for vnf in list_VNFs.split(","):
        if vnf not in VNFs:
            print ("No " + vnf)
            exit(0)

    case = list_VNFs.split(",")

    print ("Current testcase: ", case)

    run_analysis(g_config, config, case)

    # update VNF statistics
    if common.debug == False:
        database.update_vnf_stats(config)
        print ("Updated VNF statistics")

done = time.time()
elapsed = done - start
print ("Took %.2f sec (%.2f min) to analyze the testcases" % (elapsed, elapsed/60))
