#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange,dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import RemoteController

import argparse
import sys
import time

debug = 1

def debug(message):
    if debug:
        print("\033[41mDEBUG:\033[00m\033[93m" + str(message) + "\033[00m")

class ClosTopo(Topo):

    def printTopo(self, cores, fanout):
        nodespace = (cores*fanout*fanout*fanout/10)+3
        linespace = cores*fanout*fanout*fanout*nodespace+6

        cstr = ""
        astr = ""
        estr = ""
        hstr = ""
        
        for cswitch in self.coreSwArray:
            cstr += "-" + cswitch

        for aswitch in self.aggrSwArray:
            astr += "-" + aswitch

        for eswitch in self.edgeSwArray:
            estr += "-" + eswitch

        for host in self.hostsArray:
            hstr += host + "-"

        print
        print("\033[10m\033[32m"+"---CONSTRUCTED TOPOLOGY---".center(linespace+6)+"\033[00m")
        print("\033[31mCore:\033[00m-" + cstr.center(linespace, '-'))
        print("      \033[93m"+"[FULL MESH OF LINKS]".center(linespace)+"\033[00m")
        print("\033[35mAggr:\033[00m-" + astr.center(linespace, '-'))
        print("      \033[93m"+"[FULL MESH OF LINKS]".center(linespace)+"\033[00m")
        print("\033[36mEdge:\033[00m-" + estr.center(linespace, '-'))
        print("      \033[93m"+("[LINKS FROM SW TO %d HOSTS]" % fanout).center(linespace)+"\033[00m")
        print("\033[94mHost:\033[00m-" + hstr.center(linespace, '-'))
        print

        pass

    def __init__(self, fanout, cores, **opts):
        # Initialize topology and default options
        Topo.__init__(self, **opts)
        
        self.coreSwArray =[]
        self.aggrSwArray =[]
        self.edgeSwArray =[]
        self.hostsArray  =[]
       
        aggregatecnt    = cores * fanout
        edgecnt         = aggregatecnt * fanout
        hostscnt        = edgecnt * fanout

        #Set up Core and Aggregate level, Connection Core - Aggregation level
        for cnumber in range(cores):
            self.coreSwArray.append( Topo.addSwitch(self, "c"+str(cnumber)) )
            debug("Created Core Switch: c"+str(cnumber))

        for anumber in range(aggregatecnt):
            self.aggrSwArray.append( Topo.addSwitch(self, "a"+str(anumber)) )
            debug("Created Aggregate Switch: a"+str(anumber))
        
        for cswitch in self.coreSwArray:
            for aswitch in self.aggrSwArray:
                Topo.addLink( self, cswitch, aswitch )
        pass

        #Set up Edge level, Connection Aggregation - Edge level 
        for enumber in range(edgecnt):
            self.edgeSwArray.append( Topo.addSwitch(self, "e"+str(enumber)))
            debug("Created Edge Switch: e"+str(enumber))

        for aswitch in self.aggrSwArray:
            for eswitch in self.edgeSwArray:
                Topo.addLink( self, aswitch, eswitch, )
        pass
        
        #Set up Host level, Connection Edge - Host level
        for hostnumber in range(hostscnt):
            newhost = Topo.addHost(self, "h"+str(hostnumber))
            self.hostsArray.append( newhost )
            debug("Created Host: h"+str(hostnumber))

            Topo.addLink(self, newhost, self.edgeSwArray[int(hostnumber/fanout)])
            debug("Created Link: h"+str(hostnumber)+" - e"+str(int(hostnumber/fanout)))

        self.printTopo(cores, fanout)

        debug(self.switches())
        pass
	

def setup_clos_topo(fanout=2, cores=1):
    "Create and test a simple clos network"
    assert(fanout>0)
    assert(cores>0)
    topo = ClosTopo(fanout, cores)
    net = Mininet(topo=topo, controller=lambda name: RemoteController('c0', "127.0.0.1"), autoSetMacs=True, link=TCLink)
    net.start()
    time.sleep(20) #wait 20 sec for routing to converge
    net.pingAll()  #test all to all ping and learn the ARP info over this process
    CLI(net)       #invoke the mininet CLI to test your own commands
    net.stop()     #stop the emulation (in practice Ctrl-C from the CLI 
                   #and then sudo mn -c will be performed by programmer)

    
def main(argv):
    parser = argparse.ArgumentParser(description="Parse input information for mininet Clos network")
    parser.add_argument('--num_of_core_switches', '-c', dest='cores', type=int, help='number of core switches')
    parser.add_argument('--fanout', '-f', dest='fanout', type=int, help='network fanout')
    args = parser.parse_args(argv)
    setLogLevel('info')
    setup_clos_topo(args.fanout, args.cores)


if __name__ == '__main__':
    main(sys.argv[1:])