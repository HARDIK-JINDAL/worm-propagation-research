import socket
import json
import csv
import os
from datetime import datetime

COLLECTOR_PORT = 8888
LOG_DIR = os.path.expanduser("~/Desktop/project/logs/network1")

def get_log_file():
    os.makedirs(LOG_DIR, exist_ok=True)
    return os.path.join(LOG_DIR, "results.csv")

def write_header(filepath):
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "worm_type", "network",
            "source_ip", "infected_ip", "hop_count",
            "infected_chain"
        ])

def start_collector():
    filepath = get_log_file()
    write_header(filepath)
    infected_already = set()

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", COLLECTOR_PORT))
    s.listen(20)
    print(f"[*] Collector running on port {COLLECTOR_PORT}")
    print(f"[*] Saving logs to {filepath}")

    while True:
        conn, addr = s.accept()
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        conn.close()

        try:
            log = json.loads(data.decode())
            infected_ip = log.get("infected_ip")

            if infected_ip in infected_already:
                print(f"[~] Duplicate skipped: {infected_ip}")
                continue
            infected_already.add(infected_ip)

            with open(filepath, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    log.get("timestamp"),
                    log.get("worm_type"),
                    "Network_1",
                    log.get("source_ip"),
                    log.get("infected_ip"),
                    log.get("hop_count"),
                    log.get("infected_chain")
                ])
            print(f"[+] {log.get('worm_type')} | {log.get('source_ip')} → {log.get('infected_ip')} | hop {log.get('hop_count')}")

            if len(infected_already) == 5:
                print("[*] All 5 victims infected — experiment complete")

        except Exception as e:
            print(f"[-] Error: {e}")

start_collector()
