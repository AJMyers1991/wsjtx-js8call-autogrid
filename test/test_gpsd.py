#!/usr/bin/env python3
"""
Test script for GPSD functionality
Tests the direct socket communication with GPSD
"""

import socket
import json
import time

def test_gpsd_connection():
    """Test GPSD connection and data parsing."""
    print("Testing GPSD connection...")
    
    try:
        # Connect to GPSD
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 2947))
        print("✓ Connected to GPSD on localhost:2947")
        
        # Send version command
        sock.send(b'?VERSION;\n')
        version_response = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"✓ GPSD Version: {version_response.strip()}")
        
        # Send watch command to enable JSON output
        sock.send(b'?WATCH={"enable":true,"json":true};\n')
        watch_response = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"✓ Watch response: {watch_response.strip()}")
        
        # Try to read some data
        print("Reading GPS data (timeout: 5 seconds)...")
        sock.settimeout(5)
        data = sock.recv(1024).decode('utf-8', errors='ignore')
        
        if data:
            print(f"✓ Received data: {repr(data)}")
            
            # Parse JSON responses
            lines = data.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        gps_data = json.loads(line)
                        print(f"✓ Parsed JSON: {gps_data}")
                        
                        if gps_data.get('class') == 'TPV':
                            lat = gps_data.get('lat')
                            lon = gps_data.get('lon')
                            mode = gps_data.get('mode', 0)
                            print(f"✓ TPV data - lat: {lat}, lon: {lon}, mode: {mode}")
                        
                        elif gps_data.get('class') == 'SKY':
                            time_str = gps_data.get('time')
                            print(f"✓ SKY data - time: {time_str}")
                    
                    except json.JSONDecodeError as e:
                        print(f"✗ JSON decode error: {e}")
        else:
            print("✗ No data received from GPSD")
        
        sock.close()
        print("✓ GPSD connection test completed")
        
    except socket.timeout:
        print("✗ Timeout connecting to GPSD")
    except ConnectionRefusedError:
        print("✗ Connection refused - GPSD may not be running")
        print("  To start GPSD: sudo systemctl start gpsd")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_gpsd_connection() 