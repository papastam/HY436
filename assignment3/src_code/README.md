
# Assignment 3 (*Simple load balancer using [P4 Switch programming language](https://opennetworking.org/p4/)*)

## Overview
In this assignment we had to implement the same load balancer we implemented in the first assignment using the [P4 Switch programming language](https://opennetworking.org/p4/) instead of a POX controller.

The topology of the network is the following:
![Assignment 3 topology](/.README_images/ass3_topo.png)

## Files Structure (*from [assignment3 foler](/assignment3)*)
- **[assignment3.pdf](/assignment3/assignment3.pdf)**: Complete assignment description.
- **[src_code/](/assignment3/src_code)**: The folder containing the requrired code.
    - **[simple_load_balancer.p4](/assignment3/src_code/simple_load_balancer.p4)**: The P4 file containing the code of the load balancer.
    - **[slb-runtime.json](/assignment3/src_code/slb-runtime.json)**: The JSON file containing the runtime configuration of the load balancer.
    - **[reconf_lb_groups_runtime.py](/assignment3/src_code/reconf_lb_groups_runtime.py)**: The python file used to reconfigure the load balancer at runtime.
    - **[topology.json](/assignment3/src_code/topology.json)**: The JSON file containing the topology of the network.
    - **[send.py](/assignment3/src_code/send.py)**, **[recieve.py](/assignment3/src_code/recieve.py)**: The python files used to send and receive TCP packets.

## How to run

1. Requirements:
    - Get the p4 [vm image](https://drive.google.com/file/d/1ZkE5ynJrASMC54h0aqDwaCOA0I4i48AC/view) and open it in a vm tool like [VirtualBox](https://www.virtualbox.org/).
    - Upload the following files in a new directy in the `/home/p4/tutorials/exercises` folder:
        - [simple_load_balancer.py](/assignment1/simple_load_balancer.py)
        - [slb-runtime.json](/assignment3/src_code/slb-runtime.json)
        - [topology.json](/assignment3/src_code/topology.json)
        - [Makefile](/assignment3/src_code/Makefile)

2. Run the following commands (in the new directory with the files above