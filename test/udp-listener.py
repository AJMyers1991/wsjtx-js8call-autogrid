import socket

UDP_IP = "0.0.0.0"  # Listen on all interfaces
UDP_PORT = 2237

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for UDP packets on port {UDP_PORT}...")
while True:
    data, addr = sock.recvfrom(4096)
    print(f"Received packet from {addr}:")
    print(data)
    print('-' * 40) 