import socket
import json
import time
import os

JS8CALL_HOST = '127.0.0.1'
JS8CALL_PORT = 2442

# List of test grid squares to cycle through
TEST_GRIDS = [
    'EN61',
    'EN62',
    'EN63',
    'EN64',
    'EN65',
]

CHANGE_INTERVAL = 4  # seconds between changes (5 changes in 20 seconds)


def set_js8call_grid(grid, host=JS8CALL_HOST, port=JS8CALL_PORT):
    command = {
        'type': 'STATION.SET_GRID',
        'value': grid
    }
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall((json.dumps(command) + '\n').encode('utf-8'))
            try:
                response = sock.recv(1024)
                print(f"[RESPONSE] {response.decode('utf-8', errors='ignore').strip()}")
            except socket.timeout:
                print("[WARNING] No response from JS8Call (timeout)")
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to JS8Call at {host}:{port}. Is JS8Call running?")
    except Exception as e:
        print(f"[ERROR] {e}")


def main():
    print("Starting JS8Call grid change test...")
    for i, grid in enumerate(TEST_GRIDS):
        print(f"[{i+1}/5] Setting grid to: {grid}")
        set_js8call_grid(grid)
        if i < len(TEST_GRIDS) - 1:
            time.sleep(CHANGE_INTERVAL)
    print("Test complete.")


if __name__ == "__main__":
    main() 