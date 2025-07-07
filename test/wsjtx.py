import socket
import struct
import time

UDP_IP = "127.0.0.1"
UDP_PORT = 2237
SCHEMA_VERSION = 3
MAGIC_NUMBER = 0xadbccbda
PACKET_TYPE = 11  # LocationChangePacket
WSJTX_ID = "WSJT-X"  # This should match your WSJT-X id

def qstring(s):
    b = s.encode("utf-8")
    return struct.pack(">l", len(b)) + b

def build_location_change_packet(wsjtx_id, grid):
    pkt = bytearray()
    pkt += struct.pack(">L", MAGIC_NUMBER)
    pkt += struct.pack(">l", SCHEMA_VERSION)
    pkt += struct.pack(">l", PACKET_TYPE)
    pkt += qstring(wsjtx_id)
    pkt += qstring("GRID:" + grid)
    return pkt

grids = ["AA11", "BB22", "CC33", "DD44", "EE55"]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))  # Listen for status packets

print("Waiting for a status packet from WSJT-X...")
while True:
    data, addr = sock.recvfrom(2048)
    # Check for a status packet (type 1)
    if data[0:4] == struct.pack(">L", MAGIC_NUMBER):
        schema = struct.unpack(">l", data[4:8])[0]
        pkt_type = struct.unpack(">l", data[8:12])[0]
        if pkt_type == 1:
            print(f"Got status packet from {addr}")
            break

# Now send the grid updates to the address/port from which the status packet was received
for i, grid in enumerate(grids):
    pkt = build_location_change_packet(WSJTX_ID, grid)
    sock.sendto(pkt, addr)
    print(f"Sent grid update {i+1}/5 to WSJT-X at {addr}: {grid}")
    time.sleep(6)

print("All grid updates sent.") 