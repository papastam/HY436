# Software Defined Networks (*[HY436](https://www.csd.uoc.gr/~hy436/)*) 
In this repository you can find the assignments and my solutions of the course [*Software Defined Networks* (HY436)](https://www.csd.uoc.gr/~hy436/) during the winter semester of year 2022.
# Assignment 1 (*Simple Load Balancer*)
## Overview
In this assignment we had to implement a simple load balancer using the [OpenFlow protocol](https://en.wikipedia.org/wiki/OpenFlow). The load balancer had to be implemented using the [POX](https://github.com/noxrepo/pox) controller. The topology of the network was the following:
![Assignment 1 topology](/.README_images/assignment1_topo.png)

## Files Structure (*from [assignmen1 foler](/assignment1)*)
- **[assignment1.pdf](/assignment1/assignment1.pdf)**: Complete assignment description.
- **[SimpleLoadBalancer.py](/assignment1/SimpleLoadBalancer.py)**: The python file of the load balancer. It contains the code of the load balancer.
- **[SimpleLoadBalancer_conf.json](/assignment1/SimpleLoadBalancer_conf.json)**: A JSON file containing the topology description (client/server colors and IP addresses).
- **[mega-test.png](/assignment1/mega-test.png)**: A screenshot of the final test run.

## How to run

1. Requirements:
    - [Mininet](https://pypi.org/project/mininet/)
    - [POX](https://github.com/noxrepo/pox)
    - [SimpleLoadBalancer.py](/assignment1/SimpleLoadBalancer.py) needs to be in the `/pox/ext` folder.
2. Run the following commands:
    - `sudo mn --topo single,8 --controller remote --mac --switch ovsk` 
    (to create the topology)
    - `./pox.py SimpleLoadBalancer --configuration_json_file=ext/SimpleLoadBalancer_conf.json` (to run the load balancer) (This command needs to be run from the `pox` folder)

# Assignment 2 (*Clos topology*)
## Overview
In this assignment we had to implement a **Clos topology** for data centers using the [OpenFlow protocol](https://en.wikipedia.org/wiki/OpenFlow). The topology had to be implemented using the [POX](https://github.com/noxrepo/pox). The topology is created using the following two parameters:
- `c` *or* `--core` : The number of core switches.
- `f` *or* `--fanout` : The number of child nodes each node has.

The **Clos topology** has the following three layers:
- **Core layer**: The core layer is the top layer of the topology. It contains the `c` number of core switches.
- **Aggregation layer**: The aggregation layer is the middle layer of the topology. It contains the `c*f` number of aggregation switches.
- **Edge layer**: The edge layer is the bottom layer of the topology. It contains the `c*f*f` number of edge switches. Each edge switch is connected to `f` hosts.

The topology of a network with parametes `c=1` and `f=2` is the following:
![Assignment 2 topology](/.README_images/assignment2_topo.png)

## Files Structure (*from [assignmen2 foler](/assignment2)*)
- **[assignment2.pdf](/assignment2/assignment2.pdf)**: Complete assignment description.
- **[src_code/](/assignment2/src_code)**: The folder containing the requrired code.
    - **[CloudNetController.py](/assignment2/src_code/CloudNetController.py)**: The python file containing the code of the controller.
    - **[clos_topo.py](/assignment2/src_code/clos_topo.py)**: The python file used to initialize the topology.
    - **[firewall_policies.csv](/assignment2/src_code/firewall_policies.csv)**: A CSV file containing the firewall policies.
    - **[migration_events.csv](/assignment2/src_code/migration_events.csv)**: A CSV file containing the migration events.
    - **[tcp_sender.py](/assignment2/src_code/tcp_sender.py), [tcp_receiver.py](/assignment2/src_code/tcp_receiver.py), [udp_sender.py](/assignment2/src_code/udp_sender.py), [udp_receiver.py](/assignment2/src_code/udp_receiver.py)**:Python files used to send and receive TCP and UDP packets.
## How to run

1. Requirements:
    - [Mininet](https://pypi.org/project/mininet/)
    - [POX](https://github.com/noxrepo/pox)
    - [SimpleLoadBalancer.py](/assignment1/SimpleLoadBalancer.py) needs to be in the `/pox/ext` folder.
2. Run the following commands:
    - `sudo python clos_topo.py -c <# of core switches> -f <# of fanout>`
    (to create the topology)
    - `/pox.py openflow.discovery CloudNetController --firewall_capability=<True|False> --migration_capability=<True|False>` (to run the load balancer) (This command needs to be run from the `pox` folder)

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

2. Run the following commands (in the new directory with the files above):
    - `make stop ; make clean`
    (to stop and clean the last topology)
    - `make run` (to run the mininet and the load balancer)

# Assignment 4 (*[Artemis](https://github.com/FORTH-ICS-INSPIRE/artemis) Implementation*)
## Overview

For the [fourt assignment](/assignment4/HY436_assignment_4.pdf) I ran an instance of [Artemis](https://github.com/FORTH-ICS-INSPIRE/artemis) using a custom [configutation file](/assignment4/config.yaml) (code can be found below) to suit the assignment’s needs. In the config file there is a prefix watched (snd_assignment4) which is requested from the assignment. The source AS (sdn_assignment4_asn) and the neighbor AS (sdn_assignment4_neighbor) are also set up and a rule connecting ASes and prefixes is present too. Also a monitor is setup according to the basic config file from the git repository

Configuration File:
```yaml
#
# ARTEMIS Configuration File (HY436 Assignment4)
#
# Start of Prefix Definitions
prefixes:
  sdn_assignment4: &sdn_assignment4
  - 184.164.247.0/24
# End of Prefix Definitions

# Start of ASN Definitions
asns:
  sdn_assignment4_asn: &sdn_assignment4_asn
  - 61574
  sdn_assignment4_neighbor: &sdn_assignment4_neighbor
  - 47065
# End of ASN Definitions

# Start of Monitor Definitions
monitors:
  riperis: ['']
  bgpstreamlive:
  - routeviews
  - ris
  bgpstreamkafka:
    host: bmp.bgpstream.caida.org
    port: 9092
    topic: '^openbmp\.router--.+\.peer-as--.+\.bmp_raw'
  bgpstreamhist: '/etc/artemis/'
# End of Monitor Definitions

# Start of Rule Definitions
rules:
- prefixes:
  - *sdn_assignment4
  origin_asns:
  - *sdn_assignment4_asn
  neighbors:
  - *sdn_assignment4_neighbor
  mitigation: manual
# End of Rule Definitions 
```

## Results

In the screenshots included below are the [hijacks](https://bgpartemis.readthedocs.io/en/latest/hijackinfo/) found by Artemis. In total two types of hijacks were picked up by my implementation, E|0|-|- and E|1|-|-. E|0|-|- means that there was a hijack for the exact prefix (sdn_assignment4) with an illegal origin. E|1|-|- means that there was a hijack for the exact prefix (sdn_assignment4) with a legal origin but an illegal first hop. In the second screenshot an ongoing hijack can also be noticed!

- E|0|-|- hijacks: ![E|0|-|- hijacks](/assignment4/screenshots/E0_hijacks.png)

- E|1|-|- hijacks: ![E|1|-|- hijacks](/assignment4/screenshots/E1_hijacks.png)