#!/bin/bash

sshpass -p "mininet" rsync -e ssh --exclude='*/pox' src_code/* mininet@192.168.56.102:pox/ext
