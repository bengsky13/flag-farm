#!/bin/bash
set -e
cd "$(dirname "$0")"

INTERVAL=30
PCAP_DIR="`pwd`/pcaps"

tcpdump -n "(tcp or udp) and not (port 22)" -Z root -G $INTERVAL -w "${PCAP_DIR}/$IFACE_%Y%m%d_%H%M%S.pcap" -z "`pwd`/tcpdump_complete.sh"