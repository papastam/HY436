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
