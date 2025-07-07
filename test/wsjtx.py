import socket
import struct
import time

WSJTX_HOST = '127.0.0.1'
WSJTX_PORT = 2237

# List of test grid squares to cycle through
TEST_GRIDS = [
    'EN61',
    'EN62',
    'EN63',
    'EN64',
    'EN65',
]

CHANGE_INTERVAL = 4  # seconds between changes (5 changes in 20 seconds)

# WSJT-X UDP protocol constants
MAGIC_NUMBER = 0xadbccbda
SCHEMA_VERSION = 2
PACKET_TYPE_LOCATION = 11
WSJTX_ID = 'WSJT-X'  # Use a generic ID for testing


def build_wsjtx_location_packet(grid, wsjtx_id=WSJTX_ID):
    # Build a WSJT-X LocationChangePacket (see autogrid code)
    packet = bytearray()
    packet.extend(struct.pack('>L', MAGIC_NUMBER))  # Magic
    packet.extend(struct.pack('>L', SCHEMA_VERSION))  # Schema
    packet.extend(struct.pack('>l', PACKET_TYPE_LOCATION))  # Packet type (signed int)
    id_bytes = wsjtx_id.encode('utf-8')
    packet.extend(struct.pack('>l', len(id_bytes)))
    packet.extend(id_bytes)
    grid_bytes = ("GRID:" + grid).encode('utf-8')
    packet.extend(struct.pack('>l', len(grid_bytes)))
    packet.extend(grid_bytes)
    return bytes(packet)


def send_wsjtx_grid(grid, host=WSJTX_HOST, port=WSJTX_PORT):
    packet = build_wsjtx_location_packet(grid)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet, (host, port))
        print(f"[SENT] Sent grid update to WSJT-X: {grid}")
    except Exception as e:
        print(f"[ERROR] Failed to send grid update: {e}")


def main():
    print("Starting WSJT-X grid change test...")
    for i, grid in enumerate(TEST_GRIDS):
        print(f"[{i+1}/5] Setting grid to: {grid}")
        send_wsjtx_grid(grid)
        if i < len(TEST_GRIDS) - 1:
            time.sleep(CHANGE_INTERVAL)
    print("Test complete.")


if __name__ == "__main__":
    main() 