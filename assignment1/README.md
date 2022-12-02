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
