#!/bin/bash

gnome-terminal -- sh -c "sshpass -p 'mininet' bash -c \"ssh -X -t mininet@192.168.56.101 'cd pox; bash --login'\""
gnome-terminal -- sh -c "sshpass -p 'mininet' bash -c \"ssh -X -t mininet@192.168.56.101 'cd pox/ext; bash --login'\""
w