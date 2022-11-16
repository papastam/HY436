#generic imports
import sys
import os
import random
import time
import traceback
import csv

#pox-specific imports
from pox.core import core
from pox.openflow import ethernet
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
from pox.lib.packet.arp import arp
from pox.lib.addresses import EthAddr, IPAddr
from pox.lib.revent import *
from pox.lib.recoco import Timer

#networkx import for graph management
import networkx as nx

#for beautiful prints of dicts, lists, etc,
from pprint import pprint as pp

log = core.getLogger()

MAX_PHYS_PORTS  = 0xFF00
ALLOW_SPAM      = 0
DEBUG           = 1

# dict of TCP and UDP proto numbers
PROTO_NUMS = {
  6 : 'tcp',
  17: 'udp/other'
}

def debug(message):
    if DEBUG:
        print("\033[103m\033[30mDEBUG:\033[00m\033[93m " + str(message) + "\033[00m")

def warrning(message):
    print("\033[44mWARRNING:\033[00m\033[34m " + str(message) + "\033[00m")

def arpprint(message):
    print("\033[46mARP:\033[00m\033[96m " + str(message) + "\033[00m")

def ipprint(message):
    print("\033[42mIP:\033[00m\033[92m " + str(message) + "\033[00m")

def migrationprint(message):
    print("\033[45mMIGRATION:\033[00m\033[35m " + str(message) + "\033[00m")

def spampp(message):
    if ALLOW_SPAM == 1:
        pp(message)
    else:
        print("(output disabled to reduce spam)")

class CloudNetController (EventMixin):

    _neededComponents = set(['openflow_discovery'])

    def __init__(self, firewall_capability, migration_capability, firewall_policy_file, migration_events_file):
        super(EventMixin, self).__init__()

        #generic controller information
        self.switches = {}     # key=dpid, value = SwitchWithPaths instance
        self.sw_sw_ports = {}  # key = (dpid1,dpid2), value = outport of dpid1
        self.adjs = {}         # key = dpid, value = list of neighbors
        self.arpmap = {} # key=host IP, value = (mac,dpid,port)
        self._paths_computed = False #boolean to indicate if all paths are computed (converged routing)
        self.ignored_IPs = [IPAddr("0.0.0.0"), IPAddr("255.255.255.255")] #these are used by openflow discovery module

        #invoke event listeners
        if not core.listen_to_dependencies(self, self._neededComponents):
            self.listenTo(core)
        self.listenTo(core.openflow)

        #module-specific information
        self.firewall_capability = firewall_capability
        self.migration_capability = migration_capability
        self.firewall_policies = None
        self.migration_events = None
        self.migrated_IPs = None
        if self.firewall_capability:
            self.firewall_policies = self.read_firewall_policies(firewall_policy_file)
        if self.migration_capability:
            self.migration_events = self.read_migration_events(migration_events_file)
            self.old_migrated_IPs = {} #key=old_IP, value=new_IP
            self.new_migrated_IPs = {} #key=new_IP, value=old_IP
            for event in self.migration_events:
                migration_time = event[0]
                old_IP = event[1]
                new_IP = event[2]
                Timer(migration_time, self.handle_migration, args = [IPAddr(old_IP), IPAddr(new_IP)])

    def read_firewall_policies(self, firewall_policy_file):
        firewall_policies = {}
        with open(firewall_policy_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                tenant_id = row[0]
                for ip in row[1:len(row)]:
                    firewall_policies[IPAddr(ip)] = int(tenant_id)
        return firewall_policies

    def read_migration_events(self, migration_info_file):
        migration_events = []
        with open(migration_info_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                migration_time = int(row[0])
                old_ip = IPAddr(row[1])
                new_ip = IPAddr(row[2])
                migration_events.append((migration_time, old_ip, new_ip))
        return migration_events

    def _handle_ConnectionUp(self, event):
        if event.dpid not in self.switches:
            self.switches[event.dpid] = SwitchWithPaths()
            if event.dpid not in self.adjs:
                self.adjs[event.dpid] = set([])
        self.switches[event.dpid].connect(event.connection)
        #send unknown ARP and IP packets to controller (install rules for that with low priority)
        msg_ARP = of.ofp_flow_mod()
        msg_IP  = of.ofp_flow_mod()
        msg_ARP.match.dl_type = 0x0806
        msg_IP.match.dl_type  = 0x0800
        msg_ARP.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
        msg_IP.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
        msg_ARP.priority = of.OFP_DEFAULT_PRIORITY - 1
        msg_IP.priority  = of.OFP_DEFAULT_PRIORITY - 1
        event.connection.send(msg_ARP)
        event.connection.send(msg_IP)

    def _handle_ConnectionDown(self, event):
        ips_to_forget = []
        for ip in self.arpmap:
            (mac, dpid, port) = self.arpmap[ip]
            if dpid == event.dpid:
                ips_to_forget.append(ip)
        for ip in ips_to_forget:
            del self.arpmap[ip]
        if (event.dpid in self.switches):
            self.switches[event.dpid].disconnect()
            del self.switches[event.dpid]
        #let the discovery module deal with the port removals...

    def flood_on_all_switch_edges(self, packet, this_dpid, this_port):
        for src_dpid in self.switches:
            no_flood_ports = set([]) #list of non-flood ports
            if src_dpid in self.adjs:
                for nei_dpid in self.adjs[src_dpid]:
                    no_flood_ports.add(self.sw_sw_ports[(src_dpid,nei_dpid)])
            if src_dpid == this_dpid:
                no_flood_ports.add(this_port)
            self.switches[src_dpid].flood_on_switch_edge(packet, no_flood_ports)

    def update_learned_arp_info(self, packet, dpid, port):
        src_ip = None
        src_mac = None
        if packet.type == packet.ARP_TYPE:
            src_mac = EthAddr(packet.src)
            src_ip  = IPAddr(packet.next.protosrc)
        elif packet.type == packet.IP_TYPE:
            src_mac = EthAddr(packet.src)
            src_ip  = IPAddr(packet.next.srcip)
        else:
            pass
        if (src_ip != None) and (src_mac != None):
            self.arpmap[src_ip] = (src_mac, dpid, port)

    def _handle_PacketIn(self, event):
        packet = event.parsed
        dpid = event.dpid
        inport = event.port
        # debug("Packet: "+str(packet.__dict__))
        # debug("Packet.next: "+str(packet.next.protocol))

        def handle_ARP_pktin():
            srcip = IPAddr(packet.next.protosrc)
            dstip = IPAddr(packet.next.protodst)
            if (srcip in self.ignored_IPs) or (dstip in self.ignored_IPs):
                return

            if packet.next.opcode == arp.REQUEST:
                arpprint("Handling ARP packet: %s requests the MAC of %s" % (str(srcip), str(dstip)))
                self.update_learned_arp_info(packet, dpid, inport)

                #FIREWALL functionality
                if self.firewall_capability:
                    try:#CP CODE
                        if(self.firewall_policies[srcip]!=self.firewall_policies[dstip]):
                            print("\033[41mFIREWALL:\033[00m\033[31m Illegal packet detected from %s to %s\033[00m" %(srcip,dstip))
                            self.drop_packets(dpid,packet)
                            return
                    except KeyError:
                        arpprint("IPs not covered by policy!")
                        return

                if self.migration_capability:
                    #ignore ARP requests coming from old migrated IPs or directed to new ones
                    if (srcip in self.old_migrated_IPs) or (dstip in self.new_migrated_IPs):
                        warrning("ARP request from/to migrated host detected! ignoring the request...")
                        return

                if dstip in self.arpmap:
                    arpprint("I know where to send the crafted ARP reply!")
                    (req_mac, req_dpid, req_port) = self.arpmap[dstip]
                    (dst_mac, dst_dpid, dst_port) = self.arpmap[srcip]
                    self.switches[dst_dpid].send_arp_reply(packet, dst_port, req_mac)
                else:
                    arpprint("Flooding initial ARP request on all switch edges")
                    self.flood_on_all_switch_edges(packet, dpid, inport)

            elif packet.next.opcode == arp.REPLY:
                arpprint("Handling ARP packet: %s responds to %s" % (str(srcip), str(dstip)))
                self.update_learned_arp_info(packet, dpid, inport)

                #FIREWALL functionality
                if self.firewall_capability:
                    try:#CP CODE
                        if(self.firewall_policies[srcip]!=self.firewall_policies[dstip]):
                            print("\033[41mFIREWALL:\033[00m\033[31m Illegal packet detected from %s to %s\033[00m" %(srcip,dstip))
                            self.drop_packets(dpid,packet)
                            return
                    except KeyError:
                        return

                if self.migration_capability:
                    #ignore ARP replies coming from old migrated IPs or directed to new ones
                    if (srcip in self.old_migrated_IPs) or (dstip in self.new_migrated_IPs):
                        warrning("ARP request from/to migrated host detected! ignoring the request...")
                        return

                if dstip in self.arpmap.keys():
                    arpprint("I know where to send the initial ARP reply!")
                    (dst_mac, dst_dpid, dst_port) = self.arpmap[dstip]
                    self.switches[dst_dpid].send_packet(dst_port, packet)
                else:
                    arpprint("Flooding initial ARP reply on all switch edges")
                    self.flood_on_all_switch_edges(packet,dpid,inport)
            else:
                arpprint("Unknown ARP type")
                return

        def handle_IP_pktin():
            srcip = IPAddr(packet.next.srcip)
            dstip = IPAddr(packet.next.dstip)
            if (srcip in self.ignored_IPs) or (dstip in self.ignored_IPs):
                return

            ipprint("Handling IP packet between %s and %s" % (str(srcip), str(dstip)))

            #FIREWALL functionality
            if self.firewall_capability:
                try:#CP CODE
                    if(self.firewall_policies[srcip]!=self.firewall_policies[dstip]):
                        print("\033[41mFIREWALL:\033[00m\033[31m Illegal packet detected from %s to %s\033[00m" %(srcip,dstip))
                        self.drop_packets(dpid,packet)
                        return
                except KeyError:
                    ipprint("\033[41mFIREWALL:\033[00m\033[31mIPs not covered by policy!\033[00m")
                    return

            if self._paths_computed:
                debug("Routing calculations have converged")
                ipprint("Path requested for flow %s-->%s" % (str(srcip), str(dstip)))

                if dstip in self.arpmap: #I know where to send the packet
                    (dst_mac, dst_dpid, dst_port) = self.arpmap[dstip]

                    #MIGRATION functionality
                    if self.migration_capability:
                        #IP packet goes to old server after migration is done
                        if dstip in self.old_migrated_IPs:
                            (dst_mac, dst_dpid, dst_port) = self.arpmap[self.old_migrated_IPs[dstip]]
                            #install path to new server and change packet headers
                            migrationprint("Installing migrated forward path towards: old IP: %s, new IP: %s" % (str(dstip), str(self.old_migrated_IPs[dstip])))
                            self.install_migrated_end_to_end_IP_path(event, dst_dpid, dst_port, packet, forward_path=True)
                            migrationprint("Forward migrated path installed")

                        #IP packet comes from new server after migration is done
                        elif srcip in self.new_migrated_IPs:
                            (dst_mac, dst_dpid, dst_port) = self.arpmap[dstip]
                            migrationprint("Installing migrated reverse path from: old IP: %s, new IP: %s" % (str(srcip), str(self.new_migrated_IPs[srcip])))
                            self.install_migrated_end_to_end_IP_path(event, dst_dpid, dst_port, packet, forward_path=False)
                            migrationprint("Reverse migrated path installed")
                        else:
                            self.install_end_to_end_IP_path(event, dst_dpid, dst_port, packet)
                    else:
                        self.install_end_to_end_IP_path(event, dst_dpid, dst_port, packet)
                else:
                    self.flood_on_all_switch_edges(packet, dpid, inport)
            else:
                debug("Routing calculations have not converged, discarding packet")
                return

        #--------------------------------------------------------------------------------------------------------------
        if packet.type == packet.LLDP_TYPE:
            return

        elif packet.type == packet.ARP_TYPE:
            handle_ARP_pktin()
            return

        elif packet.type == packet.IP_TYPE:
            handle_IP_pktin()
            return

        else:
            #log.info("Unknown Packet type: %s" % packet.type)
            return


    def install_end_to_end_IP_path(self, event, dst_dpid, final_port, packet): #CP CODE
        source_sw = self.switches[event.dpid]

        print("\033[35mInstalling new e2e IP path %s -> %s \033[00m" %(event.parsed.next.srcip,event.parsed.next.dstip))
        if(packet.next.protocol==6):protonum=6
        else: protonum=17

        paths = source_sw._paths_per_proto[dst_dpid][protonum]
        # debug("Available paths: "+str(paths))

        selected_path = paths[random.randint(0,len(paths)-1)]
        # debug("Selected Path :"+str(selected_path))

        my_match            = of.ofp_match()
        my_match.dl_type    = 0x0800
        my_match.nw_src     = event.parsed.next.srcip
        my_match.nw_dst     = event.parsed.next.dstip
        if(packet.next.protocol==6):my_match.nw_proto = 6

        self.switches[selected_path[-1]].install_output_flow_rule(final_port, my_match,10)
        # debug("Installed new flow rule (%s -> %s)" % (selected_path[-1],"FINAL_HOST"))
        
        for linkindex in range( len(selected_path)-2, 0-1, -1): #reverse count
            self.switches[selected_path[linkindex]].install_output_flow_rule(self.sw_sw_ports[(selected_path[linkindex],selected_path[linkindex+1])], my_match, 10)
            # debug("Installed new flow rule (%s -> %s)" % (selected_path[linkindex],selected_path[linkindex+1]))

        if event.dpid == dst_dpid:
            source_sw.send_packet(final_port, event.parsed)
        else:
            self.switches[dst_dpid].send_packet(final_port, event.parsed)

    def install_migrated_end_to_end_IP_path(self, event, dst_dpid, dst_port, packet, forward_path=True):#CP CODE
        source_sw = self.switches[event.dpid]
        
        #calculate data for the new path
        if forward_path:
            new_host_ip = self.old_migrated_IPs[event.parsed.next.dstip]
        else:
            new_host_ip = self.new_migrated_IPs[event.parsed.next.srcip]
        (new_host_mac, new_host_dpid, new_host_port) = self.arpmap[new_host_ip]
            
        
        print("\033[35mInstalling new e2e migrated IP path %s -> %s \033[00m" %(event.parsed.next.srcip,event.parsed.next.dstip))
        if(packet.next.protocol==6):protonum=6
        else: protonum=17

        paths = source_sw._paths_per_proto[dst_dpid][protonum]
        # debug("Available paths: "+str(paths))

        selected_path = paths[random.randint(0,len(paths)-1)]
        # debug("Selected Path :"+str(selected_path))


        new_match            = of.ofp_match()
        new_match.dl_type    = 0x0800
        
        before_rw_match            = of.ofp_match()
        before_rw_match.dl_type    = 0x0800

        if forward_path:
            new_match.nw_src           = event.parsed.next.srcip
            new_match.nw_dst           = new_host_ip
            
            before_rw_match.nw_src     = event.parsed.next.srcip
            before_rw_match.nw_dst     = event.parsed.next.dstip
        else:
            new_match.nw_src           = new_host_ip
            new_match.nw_dst           = event.parsed.next.dstip
        
            before_rw_match.nw_src     = event.parsed.next.srcip
            before_rw_match.nw_dst     = event.parsed.next.dstip

        if(packet.next.protocol==6):
            new_match.nw_proto          = 6
            before_rw_match.nw_proto    = 6

        if event.dpid == dst_dpid:
            if forward_path:
                source_sw.install_forward_migration_rule(dst_port, new_host_mac, new_host_ip, before_rw_match, 10)
                source_sw.send_forward_migrated_packet(dst_port, new_host_mac, new_host_ip, event.parsed)
            
            else:
                source_sw.install_reverse_migration_rule(dst_port, new_host_mac, new_host_ip, before_rw_match, 10)
                source_sw.send_reverse_migrated_packet(dst_port, new_host_mac, new_host_ip, event.parsed)

        else:
            if forward_path:
                source_sw.install_forward_migration_rule(self.sw_sw_ports[(selected_path[0],selected_path[1])], new_host_mac, new_host_ip, before_rw_match, 10)
            else:
                source_sw.install_reverse_migration_rule(self.sw_sw_ports[(selected_path[0],selected_path[1])], new_host_mac, new_host_ip, before_rw_match, 10)

            self.switches[selected_path[-1]].install_output_flow_rule(dst_port, new_match,10)
            # debug("Installed new flow rule (%s -> %s)" % (selected_path[-1],"FINAL_HOST"))
            
            for linkindex in range( len(selected_path)-3, 0-1, -1): #reverse count
                self.switches[selected_path[linkindex]].install_output_flow_rule(self.sw_sw_ports[(selected_path[linkindex],selected_path[linkindex+1])], new_match, 10)
                # debug("Installed new flow rule (%s -> %s)" % (selected_path[linkindex],selected_path[linkindex+1]))

            if forward_path:
                self.switches[dst_dpid].send_forward_migrated_packet(dst_port, new_host_mac, new_host_ip, event.parsed)
            else:
                self.switches[dst_dpid].send_reverse_migrated_packet(dst_port, new_host_mac, new_host_ip, event.parsed)

    def handle_migration(self, old_IP, new_IP):
        migrationprint("Handling migration from %s to %s..." % (str(old_IP), str(new_IP)))
        # create ofp_flow_mod message to delete all flows
        # to the destination to be migrated
        msg_1 = of.ofp_flow_mod()
        match_1 = of.ofp_match()
        match_1.dl_type = 0x0800
        match_1.nw_dst = old_IP
        msg_1.match = match_1
        msg_1.command = of.OFPFC_DELETE
        # create ofp_flow_mod message to delete all flows
        # coming from the source that will host the migrated one
        msg_2 = of.ofp_flow_mod()
        match_2 = of.ofp_match()
        match_2.dl_type = 0x0800
        match_2.nw_src = new_IP
        msg_2.match = match_2
        msg_2.command = of.OFPFC_DELETE
        # send the ofp_flow_mod messages to all switches
        # leading to the destination to be migrated (or coming from the source that will host it)
        for sw in self.switches:
            self.switches[sw].connection.send(msg_1)
            migrationprint("Rules having as dest %s removed at switch: %i" % (str(old_IP), sw))
            self.switches[sw].connection.send(msg_2)
            migrationprint("Rules having as source %s removed at switch: %i" % (str(new_IP), sw))
        migrationprint("Rules deleted, now new IP e2e paths will be automatically migrated to the new IP %s" % (str(new_IP)))
        self.old_migrated_IPs[old_IP] = new_IP
        self.new_migrated_IPs[new_IP] = old_IP
        (new_mac, new_dpid, new_inport) = self.arpmap[self.old_migrated_IPs[old_IP]]
        self.arpmap[old_IP] = (new_mac, new_dpid, new_inport)
        migrationprint("Arpmap for old ip updated")

    def drop_packets(self, dpid, packet):
        match = of.ofp_match.from_packet(packet)
        self.switches[dpid].install_drop_flow_rule(match, idle_timeout=0, hard_timeout=0)

    def _handle_openflow_discovery_LinkEvent(self, event):
        self._paths_computed = False
        link = event.link
        dpid1 = link.dpid1
        port1 = link.port1
        dpid2 = link.dpid2
        port2 = link.port2
        print("\033[32mNew link discovered! (%s->%s)\033[00m" %(dpid1,dpid2))
        if dpid1 not in self.adjs:
            self.adjs[dpid1] = set([])
        if dpid2 not in self.adjs:
            self.adjs[dpid2] = set([])

        if event.added:
            self.sw_sw_ports[(dpid1,dpid2)] = port1
            self.sw_sw_ports[(dpid2,dpid1)] = port2
            self.adjs[dpid1].add(dpid2)
            self.adjs[dpid2].add(dpid1)
        else:
            if (dpid1,dpid2) in self.sw_sw_ports:
                del self.sw_sw_ports[(dpid1,dpid2)]
            if (dpid2,dpid1) in self.sw_sw_ports:
                del self.sw_sw_ports[(dpid2,dpid1)]
            if dpid2 in self.adjs[dpid1]:
                self.adjs[dpid1].remove(dpid2)
            if dpid1 in self.adjs[dpid2]:
                self.adjs[dpid2].remove(dpid1)

        # print("Current switch-to-switch ports:")
        # spampp(self.sw_sw_ports)
        # print("Current adjacencies:")
        # spampp(self.adjs)
        self._paths_computed=False
        self.checkPaths()
        if self._paths_computed == False:
            warrning("Disjoint topology, Shortest Path Routing converging")
        else:
            # print("Topology connected, Shortest paths (re)computed successfully, Routing converged")
            # print("--------------------------")
            for dpid in self.switches:
                pass
                # self.switches[dpid].printPaths()
            # print("--------------------------")

    def checkPaths(self):
        if not self._paths_computed:
            self._paths_computed = ShortestPaths(self.switches, self.adjs)
        return self._paths_computed

    def __str__(self):
        return "Cloud Network Controller"

class SwitchWithPaths (EventMixin):
    def __init__(self):
        self.connection = None
        self.dpid = None
        self.ports = None
        self._listeners = None
        self._paths = {}
        self._paths_per_proto = {}

    def __repr__(self):
        return str(self.dpid)

    def appendPaths(self, dst, paths_list):
        if dst not in self._paths:
            self._paths[dst] = []
        self._paths[dst] = paths_list
        self.getPathsperProto(dst)

    def clearPaths(self):
        self._paths = {}
        self._paths_per_proto = {}

    def getPathsperProto(self, dst):
        self._paths_per_proto[dst] = {}
        # populate the per-protocol paths
        list_of_proto_nums = sorted(list(PROTO_NUMS.keys()))
        for proto_num in list_of_proto_nums:
            self._paths_per_proto[dst][proto_num] = []         
        for i,path in enumerate(self._paths[dst]):
            proto_num = list_of_proto_nums[i % len(PROTO_NUMS)]
            self._paths_per_proto[dst][proto_num].append(self._paths[dst][i])
        # if no paths for a specific protocol, get one from the pool randomly
        for proto_num in list_of_proto_nums:
            if len(self._paths_per_proto[dst][proto_num]) == 0:
                self._paths_per_proto[dst][proto_num] = [random.choice(self._paths[dst])]

    def printPaths(self):
        for dst in self._paths:
            equal_paths_number = len(self._paths[dst])
            if equal_paths_number > 1:
                print("There are %i shortest paths from switch %i to switch %i:" % (equal_paths_number, self.dpid, dst))
            else:
                print("There is exactly one shortest path from switch %i to switch %i:" % (self.dpid, dst))
            for proto_num in self._paths_per_proto[dst]:
                print("---%s (%s) paths---" % (str(PROTO_NUMS[proto_num]), str(proto_num)))
                for path in self._paths_per_proto[dst][proto_num]:
                    for u in path:
                        print("%i," % (u),)
                    print("")

    def connect(self, connection):
        if self.dpid is None:
            self.dpid = connection.dpid
        assert(self.dpid == connection.dpid)
        if self.ports is None:
            self.ports = connection.features.ports
        print("\033[32mConnect %s\033[00m" % (connection))
        self.connection = connection
        self._listeners = self.listenTo(connection)

    def disconnect(self):
        if self.connection is not None:
            print("\033[31mDisconnect %s\033[00m" % (self.connection))
            self.connection.removeListeners(self._listeners)
            self.connection = None
            self._listeners = None

    def flood_on_switch_edge(self, packet, no_flood_ports): #CP CODE
        # debug("flooding given packet on all switch edges (sw:%d)" % (self.dpid))
        
        for port in self.ports:
            # debug("DC: %s in %s"%(port.port_no,no_flood_ports))
            if (port.port_no in no_flood_ports) or (port.port_no == 65534):
                # debug("no_flood_port detected (%d)"%port.port_no)
                continue
            # debug("forwarding packet to port: "+str(port))
            self.send_packet(port.port_no, packet)
        
    def send_packet(self, outport, packet_data=None):
        msg = of.ofp_packet_out(in_port=of.OFPP_NONE)
        msg.data = packet_data
        msg.actions.append(of.ofp_action_output(port=outport))
        self.connection.send(msg)

    def send_arp_reply(self, packet, dst_port, req_mac): #CP CODE
        #craft arp reply
        r = arp()

        r.hwtype = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.hwlen = 6
        r.protolen = r.protolen

        r.opcode    = r.REPLY
        r.hwsrc     = req_mac
        r.hwdst     = packet.src
        r.protodst  = packet.payload.protosrc
        r.protosrc  = packet.payload.protodst 

        #craft ethernet packet
        e = ethernet(type=ethernet.ARP_TYPE, src=req_mac, dst=packet.src)
        e.set_payload(r)

        #send packet
        arpprint("Sending arp packet (%s) to port %s"%(str(e),str(dst_port)))
        self.send_packet(dst_port,e.pack())

    def install_output_flow_rule(self, outport, match, idle_timeout=0, hard_timeout=0):
        msg=of.ofp_flow_mod()
        msg.match = match
        msg.command = of.OFPFC_MODIFY_STRICT
        msg.idle_timeout = idle_timeout
        msg.hard_timeout = hard_timeout
        msg.actions.append(of.ofp_action_output(port=outport))
        self.connection.send(msg)

    def install_drop_flow_rule(self, match, idle_timeout=0, hard_timeout=0):
        msg=of.ofp_flow_mod()
        msg.match = match
        msg.command = of.OFPFC_MODIFY_STRICT
        msg.idle_timeout = idle_timeout
        msg.hard_timeout = hard_timeout
        msg.actions = [] #empty action list for dropping packets
        self.connection.send(msg)

    '''DEBUG: {'src': EthAddr('00:00:00:00:00:02'), 'hdr_len': 14, 'dst': EthAddr('00:00:00:00:00:04'), 'payload_len': 84, 'next': <pox.lib.packet.ipv4.ipv4 object at 0xa94efec>, 'prev': None, 'type': 2048, 'parsed': True}
    DEBUG: {'frag': 0, 'csum': 42839, 'dstip': IPAddr('10.0.0.4'), 'protocol': 1, 'srcip': IPAddr('10.0.0.2'), 'tos': 0, 'ttl': 64, 'iplen': 84, 'next': <pox.lib.packet.icmp.icmp object at 0xa94ef4c>, 'flags': 0, 'hl': 5, 'v': 4, 'id': 48972, 'prev': <pox.lib.packet.ethernet.ethernet object at 0xa94ef8c>, 'parsed': True}'''
    
    def send_forward_migrated_packet(self, outport, dst_mac, dst_ip, packet_data=None):#CP CODE
        #rewrite packet fields
        packet_data.dst = dst_mac
        packet_data.next.dstip = dst_ip

        self.send_packet(outport, packet_data)

    def send_reverse_migrated_packet(self, outport, src_mac, src_ip, packet_data=None):#CP CODE
        #rewrite packet fields
        packet_data.src = src_mac
        packet_data.next.srcip = src_ip

        self.send_packet(outport, packet_data)
        
    def install_forward_migration_rule(self, outport, dst_mac, dst_ip, match, idle_timeout=0, hard_timeout=0):#CP CODE
        migrationprint("Installed rewriting rule to switch %s for migrated address: %s through port %s" %(str(self.dpid), str(dst_ip), str(outport)))
        
        msg = of.ofp_flow_mod()
        msg.idle_timeout=idle_timeout

        debug(dst_ip)
        msg.match = match

        msg.actions.append(of.ofp_action_nw_addr.set_dst(dst_ip)) #replace destination ip as the chosen server ip
        msg.actions.append(of.ofp_action_dl_addr.set_dst(EthAddr(dst_mac)))#mac address of the chosen server
        msg.actions.append(of.ofp_action_output(port = outport)) #and send it to the chosen server's port

        self.connection.send(msg)

    def install_reverse_migration_rule(self, outport, src_mac, src_ip, match, idle_timeout=0, hard_timeout=0):#CP CODE
        migrationprint("Installed \033[04mreturn\033[00m\033[35m rewriting rule to switch %s for migrated address: %s through port %s" %(str(self.dpid), str(src_ip), str(outport)))
        
        msg = of.ofp_flow_mod()
        msg.idle_timeout=idle_timeout

        msg.match = match

        msg.actions.append(of.ofp_action_nw_addr.set_src(src_ip)) #replace destination ip as the chosen server ip
        msg.actions.append(of.ofp_action_dl_addr.set_src(EthAddr(src_mac)))#mac address of the chosen server
        msg.actions.append(of.ofp_action_output(port = outport)) #and send it to the chosen server's port

        self.connection.send(msg)
        pass


def ShortestPaths(switches, adjs):#CP CODE
    topograph = nx.Graph()

    for dpid in adjs:
        topograph.add_node(dpid)
        for neighbor in adjs.get(dpid):
            topograph.add_edge(dpid, neighbor)

    for switch in switches:
        for target in switches:
            try:
                switches[switch].appendPaths(target, list(nx.all_shortest_paths(topograph,switch,target)))
            except nx.NetworkXNoPath:
                pass

    return True
    
def str_to_bool(str):
    assert(str in ['True', 'False'])
    if str=='True':
        return True
    else:
        return False

        
def launch(firewall_capability='True', migration_capability='True',
           firewall_policy_file='./ext/firewall_policies.csv', migration_events_file='./ext/migration_events.csv'):
    """
    Args:
        firewall_capability  : boolean, True/False
        migration_capability : boolean, True/False
        firewall_policy_file : string, filename of the csv file with firewall policies
        migration_info_file  : string, filename of the csv file with migration information
    """
    print("\033[03mLoading Cloud Network Controller\033[00m")
    firewall_capability = str_to_bool(firewall_capability)
    if firewall_capability:
        print("\033[03m\033[92mFirewall Capability \033[04mENABLED\033[00m")
    else:
        print("\033[03m\033[31mFirewall Capability \033[04mDISABLED\033[00m")

    migration_capability = str_to_bool(migration_capability)
    if migration_capability:
        print("\033[03m\033[92mMigration Capability \033[04mENABLED\033[00m")
    else:
        print("\033[03m\033[31mMigration Capability \033[04mDISABLED\033[00m")
        
    core.registerNew(CloudNetController, firewall_capability, migration_capability, firewall_policy_file, migration_events_file)
    print("\033[03mNetwork Controller loaded\033[00m")
