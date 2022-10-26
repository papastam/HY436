from cgitb import reset
from turtle import color
from pox.core import core
from pox.openflow import *
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.arp import arp
from pox.lib.packet.ipv4 import ipv4
from pox.lib.addresses import EthAddr, IPAddr
log = core.getLogger()
import time
import random
import json # addition to read configuration from file

from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST

class colors:
    yellow      = "\033[93m"
    blue        = '\033[94m'
    red         = '\033[31m'
    green       = '\033[92m'
    purple      = '\033[35m'
    reset       = '\033[00m'
    underline   = '\033[04m'


FLOW_IDLE_TIMEOUT = 10
FLOW_HARD_TIMEOUT = 10

class SimpleLoadBalancer(object):
    #An ARP table containing the pair (IP, port) for each IP
    arpTable={}

    lb_choise={
        IPAddr("10.0.0.1"):IPAddr("10.0.0.5"),
        IPAddr("10.0.0.2"):IPAddr("10.0.0.6"),
        IPAddr("10.0.0.3"):IPAddr("10.0.0.7"),
        IPAddr("10.0.0.4"):IPAddr("10.0.0.8")
        }

    def mac_wcolor(self,mac):
        returnstr = ""
        lastint = int(str(mac)[-1])

        if mac == self.lb_mac:
            returnstr += colors.reset
            returnstr += colors.green
        elif lastint < 5 and lastint > 0: 
            returnstr += colors.reset
            if lastint < 3:
                returnstr += colors.red
            else:
                returnstr += colors.blue
        elif lastint >= 5 and lastint < 9: 
            returnstr += colors.underline
            if lastint < 7:
                returnstr += colors.red
            else:
                returnstr += colors.blue
        else:
            returnstr += colors.reset + colors.reset

        returnstr += str(mac) + colors.reset
        return returnstr

    #A colofuul way to display ips
    def ip_wcolor(self,ip):
        returnstr = ""

        if ip in self.user_ip_to_group:
            returnstr = colors.reset
            if self.user_ip_to_group[ip] == "red":
                returnstr += colors.red
            else:
                returnstr += colors.blue

        elif ip in self.server_ip_to_group:
            returnstr = colors.underline
            if self.server_ip_to_group[ip] == "red":
                returnstr += colors.red
            else:
                returnstr += colors.blue

        elif ip == self.service_ip:
            returnstr = colors.underline + colors.green

        else:
            returnstr = colors.reset + colors.reset

        returnstr += str(ip) + colors.reset
        return returnstr


    #a print function to print the ARP table
    def print_arp_table(self):
        print("\n{:^44}".format("Switch ARP table"))
        print("|{:^15}".format("IP") + "|{:^19}".format("MAC") + "|{:^6}|".format("PORT"))
        for item in self.arpTable.items():
            print("+---------------+-------------------+------+")
            print("|{:^30}".format(self.ip_wcolor(item[0])) + "|{:^34}".format(self.mac_wcolor(item[1][0])) + "|{:^6}|".format(item[1][1]))
        print("--------------------------------------------")

    #update the ARP table when a new packet arrives
    def update_ARP_table(self, ip, mac, inport):
        if(ip in self.arpTable) and (self.arpTable[ip] == (mac,inport)):
            log.info(colors.yellow + "APR entry for IP: " + self.ip_wcolor(ip) + colors.yellow + " already exists" + colors.reset)
        elif (ip in self.arpTable):
            self.arpTable[ip]=(mac,inport)
            log.info(colors.yellow + "ARP entry exists, but got updated! (for IP " + self.ip_wcolor(ip) + colors.yellow + ")" + colors.reset)
        else:
            self.arpTable[ip]=(mac,inport)
            log.info(colors.yellow + "New ARP entry for IP: " + self.ip_wcolor(ip) + colors.yellow + " installed" + colors.reset)


    # initialize SimpleLoadBalancer class instance
    def __init__(self, lb_mac = None, service_ip = None, 
                 server_ips = [], user_ip_to_group = {}, server_ip_to_group = {}):
        
        # add the necessary openflow listeners
        core.openflow.addListeners(self)

        # set class parameters
        self.lb_mac = lb_mac
        self.service_ip = service_ip
        self.server_ips = server_ips
        self.user_ip_to_group = user_ip_to_group
        self.server_ip_to_group = server_ip_to_group
        pass


    # respond to switch connection up event
    def _handle_ConnectionUp(self, event):
        self.connection = event.connection
        # write your code here!!!
        log.info(colors.purple+"Switch " + str(event.connection) + " has come up."+colors.reset )
        
        for(ip, group) in self.user_ip_to_group.items():
            self.send_proxied_arp_request(event.connection, ip)

        log.info(colors.purple+"Sent ARP requests to all hosts"+colors.reset)

        for(ip, group) in self.server_ip_to_group.items():
            self.send_proxied_arp_request(event.connection, ip)
        
        log.info(colors.purple+"Sent ARP requests to all servers"+colors.reset)
        pass


    # update the load balancing choice for a certain client
    def update_lb_mapping(self, client_ip):
        choise = random.randint(0,1)

        if(str(client_ip)[-1]=="1") or (str(client_ip)[-1]=="2"):
            choise += 5
        elif(str(client_ip)[-1]=="3") or (str(client_ip)[-1]=="4"):
            choise += 7
        else: #imposible case
            print(colors.red + "The impossible has happend in update_lb_mapping!" + colors.reset)
        
        if(choise == 5): self.lb_choise[client_ip]=IPAddr("10.0.0.5")  
        elif(choise == 6): self.lb_choise[client_ip]=IPAddr("10.0.0.6")
        elif(choise == 7): self.lb_choise[client_ip]=IPAddr("10.0.0.7")
        elif(choise == 8): self.lb_choise[client_ip]=IPAddr("10.0.0.8")  
            

        pass
    

    # send ARP reply "proxied" by the controller (on behalf of another machine in network)
    def send_proxied_arp_reply(self, packet, connection, outport, requested_mac):
        #craft arp reply
        r = arp()
        r.opcode    = r.REPLY
        r.hwsrc     = requested_mac
        r.hwdst     = packet.src
        r.protodst  = packet.payload.protosrc

        if(packet.payload.protosrc in self.server_ip_to_group):
            r.protosrc = packet.payload.protodst
        elif(packet.payload.protosrc in self.user_ip_to_group):
            r.protosrc = self.service_ip 

        #craft ethernet packet
        e = ethernet(type=ethernet.ARP_TYPE, src=self.lb_mac, dst=packet.payload.hwsrc)
        e.set_payload(r)

        msg         = of.ofp_packet_out()
        msg.data    = e.pack()
        msg.in_port = outport
        msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
        connection.send(msg)
        
        log.info(colors.yellow + "Sent ARP reply to " + self.ip_wcolor(packet.payload.protosrc) + colors.yellow + " from " + self.mac_wcolor(requested_mac) + colors.reset)
        pass


    # send ARP request "proxied" by the controller (so that the controller learns about another machine in network)
    def send_proxied_arp_request(self, connection, ip):
        r = arp()
        r.hwtype    = r.HW_TYPE_ETHERNET
        r.prototype = r.PROTO_TYPE_IP
        r.hwlen     = 6
        r.protolen  = r.protolen
        r.opcode    = r.REQUEST
        r.hwsrc     = self.lb_mac
        r.protosrc  = self.service_ip
        r.hwdst     = ETHER_BROADCAST
        r.protodst  = ip

        e = ethernet(type=ethernet.ARP_TYPE, src=self.lb_mac, dst=ETHER_BROADCAST)
        e.set_payload(r)

        msg         = of.ofp_packet_out()
        msg.data    = e.pack()
        msg.in_port = of.OFPP_NONE
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        connection.send(msg)
        
        log.info(colors.yellow + "Sent ARP request to " + self.ip_wcolor(ip) + colors.reset)
        pass  
    
    # install flow rule from a certain client to a certain server
    def install_flow_rule_client_to_server(self, connection, outport, client_ip, server_ip, buffer_id=of.NO_BUFFER):
        # write your code here!!!
        self.update_lb_mapping(client_ip)
        chosen_server_ip = self.lb_choise[client_ip]
        chosen_server_mac = self.arpTable[chosen_server_ip][0]
        chosen_server_port = self.arpTable[chosen_server_ip][1]

        msg = of.ofp_flow_mod()

        msg.idle_timeout=FLOW_IDLE_TIMEOUT
        msg.hard_timeout=FLOW_HARD_TIMEOUT
        
        msg.match.dl_type = 0x0800
        msg.match.nw_proto = 1
        
        msg.match.nw_dst = self.service_ip
        msg.match.nw_src = client_ip

        msg.buffer_id = buffer_id

        msg.actions.append(of.ofp_action_nw_addr.set_dst(chosen_server_ip))
        msg.actions.append(of.ofp_action_dl_addr.set_dst(chosen_server_mac))
        msg.actions.append(of.ofp_action_output(port = chosen_server_port))
        connection.send(msg)
        
        log.info("")
        log.info(colors.green + "Installed flow for route %s -> %s" %( self.ip_wcolor(client_ip), self.ip_wcolor(chosen_server_ip))  )
        pass


    # install flow rule from a certain server to a certain client
    def install_flow_rule_server_to_client(self, connection, outport, server_ip, client_ip, buffer_id=of.NO_BUFFER):
        msg = of.ofp_flow_mod()

        # msg.idle_timeout=of.OFP_FLOW_PERMANENT
        # msg.hard_timeout=of.OFP_FLOW_PERMANENT
        
        msg.match.dl_type = 0x0800
        msg.match.nw_proto = 1

        msg.match.nw_dst = client_ip

        msg.buffer_id = buffer_id

        msg.actions.append(of.ofp_action_nw_addr.set_src(self.service_ip))
        msg.actions.append(of.ofp_action_dl_addr.set_src(self.lb_mac))
        msg.actions.append(of.ofp_action_dl_addr.set_dst(self.arpTable[client_ip][0]))
        msg.actions.append(of.ofp_action_output(port = outport))
        connection.send(msg)
        
        log.info("")
        log.info(colors.green + "Installed flow for route %s -> %s" %(self.ip_wcolor(server_ip), self.ip_wcolor(client_ip))  )
        
        pass


    # main packet-in handling routine
    def _handle_PacketIn(self, event):
        packet = event.parsed
        connection = event.connection
        inport = event.port

        if packet.type == packet.ARP_TYPE:
            if packet.payload.opcode == arp.REQUEST:

                if (packet.payload.protodst == self.service_ip) or (packet.payload.protodst in self.user_ip_to_group):
                    log.info("")
                    log.info(colors.yellow + "Received ARP request for " + self.ip_wcolor(packet.payload.protodst) + colors.yellow + " from " + self.ip_wcolor(packet.payload.protosrc))
                    self.send_proxied_arp_reply(packet, connection, inport, self.lb_mac)

            elif packet.payload.opcode == arp.REPLY:
                log.info(colors.yellow + "Received ARP reply for "+ colors.green +"service IP"+colors.yellow+" from " + self.ip_wcolor(packet.payload.protosrc) + colors.reset)
                if packet.payload.hwdst == self.lb_mac:
                    self.update_ARP_table(packet.payload.protosrc, packet.payload.hwsrc, inport)
                    self.print_arp_table()
            pass
        elif packet.type == packet.IP_TYPE:

            if (packet.next.srcip in self.user_ip_to_group):
                destination_from_arp = self.arpTable[self.lb_choise[packet.next.srcip]]

                self.install_flow_rule_client_to_server(connection, destination_from_arp[1], packet.next.srcip, self.lb_choise[packet.next.srcip],event.ofp.buffer_id)

            elif (packet.next.srcip in self.server_ip_to_group):
                destination_from_arp = self.arpTable[packet.next.dstip]

                self.install_flow_rule_server_to_client(connection, destination_from_arp[1], packet.next.srcip, packet.next.dstip, event.ofp.buffer_id)
            pass
        return


# extra function to read json files
def load_json_dict(json_file):
    json_dict = {}    
    with open(json_file, 'r') as f:
        json_dict = json.load(f)
    return json_dict


# main launch routine
def launch(configuration_json_file):
    log.info("Loading Simple Load Balancer module")
    
    # load the configuration from file    
    configuration_dict = load_json_dict(configuration_json_file)   

    # the service IP that is publicly visible from the users' side   
    service_ip = IPAddr(configuration_dict['service_ip'])

    # the load balancer MAC with which the switch responds to ARP requests from users/servers
    lb_mac = EthAddr(configuration_dict['lb_mac'])

    # the IPs of the servers
    server_ips = [IPAddr(x) for x in configuration_dict['server_ips']]    

    # map users (IPs) to service groups (e.g., 10.0.0.5 to 'red')    
    user_ip_to_group = {}
    for user_ip,group in configuration_dict['user_groups'].items():
        user_ip_to_group[IPAddr(user_ip)] = group

    # map servers (IPs) to service groups (e.g., 10.0.0.1 to 'blue')
    server_ip_to_group = {}
    for server_ip,group in configuration_dict['server_groups'].items():
        server_ip_to_group[IPAddr(server_ip)] = group

    # do the launch with the given parameters
    core.registerNew(SimpleLoadBalancer, lb_mac, service_ip, server_ips, user_ip_to_group, server_ip_to_group)
    log.info("Simple Load Balancer module loaded")
