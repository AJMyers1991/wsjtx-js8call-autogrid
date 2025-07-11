#!/usr/bin/env python3
"""
WSJT-X/JS8-Call Auto Grid Square Updater
=========================================

Automatically updates grid square location in WSJT-X and JS8-Call based on GPS data.
Supports multiple GPS sources: serial, network (TCP/UDP), and GPSD.

Author: Auto-generated
License: MIT
"""

import os
import sys
import time
import json
import socket
import struct
import logging
import threading
import configparser
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple, Dict, Any
import psutil
import platform
import subprocess
import ctypes

# Import serial for GPS communication
try:
    import serial
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# GPSD support is now built-in - no external module required

# Import configparser for configuration
try:
    import configparser
except ImportError:
    print("Error: configparser not available (should be built-in)")
    sys.exit(1)


class ConfigManager:
    """Manages configuration file loading and validation."""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load and validate configuration file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        self.config.read(self.config_file)
        self.validate_config()
    
    def validate_config(self):
        """Validate configuration settings."""
        required_sections = ['GPS', 'LOGGING', 'APPLICATIONS']
        for section in required_sections:
            if not self.config.has_section(section):
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate GPS source
        gps_source = self.config.get('GPS', 'gps_source', fallback='network')
        if gps_source not in ['network', 'serial', 'gpsd']:
            raise ValueError(f"Invalid GPS source: {gps_source}")
        
        # Validate log level
        log_level = self.config.get('LOGGING', 'log_level', fallback='INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {log_level}")
    
    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get configuration value with fallback."""
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get integer configuration value with fallback."""
        return self.config.getint(section, key, fallback=fallback)
    
    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get boolean configuration value with fallback."""
        return self.config.getboolean(section, key, fallback=fallback)


class LogManager:
    """Manages logging configuration and log file rotation."""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.log_dir = "logs"
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        # Create logs directory if it doesn't exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Clean old log files
        self.cleanup_old_logs()
        
        # Setup logging format
        log_level_str = self.config.get('LOGGING', 'log_level', fallback='INFO').upper()
        log_level = logging.DEBUG if log_level_str == 'DEBUG' else logging.INFO
        debug_mode = self.config.getboolean('LOGGING', 'debug_mode', fallback=False)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"autogrid_{timestamp}.log")
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler() if debug_mode else logging.NullHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging initialized")
    
    def cleanup_old_logs(self):
        """Remove old log files, keeping only the most recent ones."""
        keep_logs = self.config.getint('LOGGING', 'keep_logs', fallback=5)
        
        if not os.path.exists(self.log_dir):
            return
        
        # Get all log files
        log_files = []
        for file in os.listdir(self.log_dir):
            if file.startswith("autogrid_") and file.endswith(".log"):
                log_files.append(os.path.join(self.log_dir, file))
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Remove old files
        for old_file in log_files[keep_logs:]:
            try:
                os.remove(old_file)
                print(f"Removed old log file: {old_file}")
            except OSError as e:
                print(f"Error removing old log file {old_file}: {e}")


class GridConverter:
    """Converts GPS coordinates to Maidenhead grid squares."""
    
    def __init__(self, precision: int = 4):
        self.precision = precision
        self.upper = 'ABCDEFGHIJKLMNOPQRSTUVWX'
        self.lower = 'abcdefghijklmnopqrstuvwx'
    
    def lat_lon_to_grid(self, lat: float, lon: float) -> str:
        """
        Convert latitude and longitude to Maidenhead grid square.
        
        Args:
            lat: Latitude in decimal degrees (-90 to 90)
            lon: Longitude in decimal degrees (-180 to 180)
        
        Returns:
            Maidenhead grid square string
        """
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
        if not (-180 <= lon <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
        
        # Adjust coordinates
        adj_lat = lat + 90.0
        adj_lon = lon + 180.0
        
        # Calculate grid square
        grid_lon_sq = self.upper[int(adj_lon / 20)]
        grid_lat_sq = self.upper[int(adj_lat / 10)]
        
        grid_lon_field = str(int((adj_lon / 2) % 10))
        grid_lat_field = str(int(adj_lat % 10))
        
        grid = grid_lon_sq + grid_lat_sq + grid_lon_field + grid_lat_field
        
        # Add subsquare if 6-character precision requested
        if self.precision == 6:
            adj_lat_remainder = (adj_lat - int(adj_lat)) * 60
            adj_lon_remainder = ((adj_lon) - int(adj_lon / 2) * 2) * 60
            
            grid_lon_subsq = self.lower[int(adj_lon_remainder / 5)]
            grid_lat_subsq = self.lower[int(adj_lat_remainder / 2.5)]
            
            grid += grid_lon_subsq + grid_lat_subsq
        
        return grid


class NMEAParser:
    """Parses NMEA sentences to extract GPS coordinates."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.last_utc_time = None
    
    def parse_nmea_sentence(self, sentence: str) -> Optional[Tuple[float, float]]:
        """
        Parse NMEA sentence and extract latitude/longitude.
        """
        try:
            sentence = sentence.strip()
            if not sentence.startswith('$'):
                return None
            parts = sentence.split(',')
            if len(parts) < 6:
                return None
            sentence_type = parts[0]
            if sentence_type == '$GPGLL':
                return self._parse_gpgll(parts)
            elif sentence_type == '$GPGGA':
                return self._parse_gpgga(parts)
            elif sentence_type == '$GPRMC':
                return self._parse_gprmc(parts)
            elif sentence_type == '$GPGNS' or sentence_type == '$GNGNS':
                return self._parse_gns(parts)
            elif sentence_type == '$GPBWC':
                return self._parse_bwc(parts)
            elif sentence_type == '$GPRMB':
                return self._parse_rmb(parts)
            elif sentence_type == '$GPWPL':
                return self._parse_wpl(parts)
            elif sentence_type == '$GPAPB':
                return self._parse_apb(parts)
            elif sentence_type == '$GPVTG':
                return self._parse_gpvtg(parts)
            elif sentence_type == '$GPZDA':
                return self._parse_zda(parts)
            else:
                return self._parse_generic(parts)
        except Exception as e:
            self.logger.debug(f"Error parsing NMEA sentence: {e}")
            return None

    def _parse_gpgll(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse GPGLL sentence."""
        try:
            if len(parts) < 7:
                return None
            
            lat_raw = parts[1]
            lat_dir = parts[2]
            lon_raw = parts[3]
            lon_dir = parts[4]
            time_str = parts[5]
            status = parts[6]
            
            if status != 'A':  # Not active
                return None
            
            self.last_utc_time = self._parse_nmea_time(time_str, "")
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            
            return (lat, lon)
        except:
            return None
    
    def _parse_gpgga(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse GPGGA sentence."""
        try:
            if len(parts) < 15:
                return None
            
            time_str = parts[1]
            lat_raw = parts[2]
            lat_dir = parts[3]
            lon_raw = parts[4]
            lon_dir = parts[5]
            fix_quality = parts[6]
            
            if fix_quality == '0':  # No fix
                return None
            
            self.last_utc_time = self._parse_nmea_time(time_str, "")
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            
            return (lat, lon)
        except:
            return None
    
    def _parse_gprmc(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse GPRMC sentence."""
        try:
            if len(parts) < 12:
                return None
            
            time_str = parts[1]
            status = parts[2]
            lat_raw = parts[3]
            lat_dir = parts[4]
            lon_raw = parts[5]
            lon_dir = parts[6]
            date_str = parts[9] if len(parts) > 9 and parts[9] else ""
            
            if status != 'A':  # Not active
                return None
            
            self.last_utc_time = self._parse_nmea_time(time_str, date_str)
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            
            return (lat, lon)
        except:
            return None
    
    def _parse_gpvtg(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse GPVTG sentence (note: this doesn't contain position data)."""
        return None  # VTG contains track and speed, not position
    
    def _parse_generic(self, parts: list) -> Optional[Tuple[float, float]]:
        """Generic parsing for other NMEA sentence types."""
        # Look for common patterns in other sentence types
        for i, part in enumerate(parts):
            if self._looks_like_lat(part) and i + 1 < len(parts):
                lat_dir = parts[i + 1]
                if lat_dir in ['N', 'S']:
                    # Look for longitude in subsequent parts
                    for j in range(i + 2, len(parts) - 1):
                        if self._looks_like_lon(parts[j]) and parts[j + 1] in ['E', 'W']:
                            try:
                                lat = self._convert_nmea_coord(part, lat_dir)
                                lon = self._convert_nmea_coord(parts[j], parts[j + 1])
                                return (lat, lon)
                            except:
                                pass
        return None
    
    def _looks_like_lat(self, value: str) -> bool:
        """Check if a value looks like a latitude coordinate."""
        try:
            if not value or '.' not in value:
                return False
            parts = value.split('.')
            if len(parts) != 2:
                return False
            degrees = int(parts[0][:-2])  # Remove minutes
            minutes = float(parts[0][-2:] + '.' + parts[1])
            return 0 <= degrees <= 90 and 0 <= minutes < 60
        except:
            return False
    
    def _looks_like_lon(self, value: str) -> bool:
        """Check if a value looks like a longitude coordinate."""
        try:
            if not value or '.' not in value:
                return False
            parts = value.split('.')
            if len(parts) != 2:
                return False
            degrees = int(parts[0][:-2])  # Remove minutes
            minutes = float(parts[0][-2:] + '.' + parts[1])
            return 0 <= degrees <= 180 and 0 <= minutes < 60
        except:
            return False
    
    def _convert_nmea_coord(self, coord_str: str, direction: str) -> float:
        """Convert NMEA coordinate format to decimal degrees."""
        if not coord_str or not direction:
            raise ValueError("Invalid coordinate or direction")
        
        # NMEA format: DDMM.MMMM (degrees and decimal minutes)
        dot_pos = coord_str.find('.')
        if dot_pos < 2:
            raise ValueError(f"Invalid NMEA coordinate format: {coord_str}")
        
        degrees = float(coord_str[:dot_pos - 2])
        minutes = float(coord_str[dot_pos - 2:])
        
        decimal_degrees = degrees + (minutes / 60.0)
        
        # Apply direction
        if direction in ['S', 'W']:
            decimal_degrees = -decimal_degrees
        
        return decimal_degrees

    def _parse_gns(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse GNS sentence (GNSS Fix Data)."""
        try:
            if len(parts) < 6:
                return None
            time_str = parts[1]
            lat_raw = parts[2]
            lat_dir = parts[3]
            lon_raw = parts[4]
            lon_dir = parts[5]
            if not lat_raw or not lon_raw:
                return None
            self.last_utc_time = self._parse_nmea_time(time_str, "")
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            self.logger.debug(f"[GNS] Parsed lat={lat}, lon={lon}")
            return (lat, lon)
        except Exception as e:
            self.logger.debug(f"Error parsing GNS: {e}")
            return None

    def _parse_bwc(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse BWC sentence (Bearing and Distance to Waypoint)."""
        try:
            if len(parts) < 7:
                return None
            lat_raw = parts[3]
            lat_dir = parts[4]
            lon_raw = parts[5]
            lon_dir = parts[6]
            if not lat_raw or not lon_raw:
                return None
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            self.logger.debug(f"[BWC] Parsed lat={lat}, lon={lon}")
            return (lat, lon)
        except Exception as e:
            self.logger.debug(f"Error parsing BWC: {e}")
            return None

    def _parse_rmb(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse RMB sentence (Recommended Minimum Navigation Info)."""
        try:
            if len(parts) < 10:
                return None
            lat_raw = parts[6]
            lat_dir = parts[7]
            lon_raw = parts[8]
            lon_dir = parts[9]
            if not lat_raw or not lon_raw:
                return None
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            self.logger.debug(f"[RMB] Parsed lat={lat}, lon={lon}")
            return (lat, lon)
        except Exception as e:
            self.logger.debug(f"Error parsing RMB: {e}")
            return None

    def _parse_wpl(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse WPL sentence (Waypoint Location)."""
        try:
            if len(parts) < 5:
                return None
            lat_raw = parts[1]
            lat_dir = parts[2]
            lon_raw = parts[3]
            lon_dir = parts[4]
            if not lat_raw or not lon_raw:
                return None
            lat = self._convert_nmea_coord(lat_raw, lat_dir)
            lon = self._convert_nmea_coord(lon_raw, lon_dir)
            self.logger.debug(f"[WPL] Parsed lat={lat}, lon={lon}")
            return (lat, lon)
        except Exception as e:
            self.logger.debug(f"Error parsing WPL: {e}")
            return None

    def _parse_apb(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse APB sentence (Autopilot Sentence B)."""
        try:
            # APB can contain bearing/waypoint info, but lat/lon is not always present. Try to extract if available.
            # There is no strict standard for lat/lon in APB, but some devices may include it in specific fields.
            # We'll attempt to find lat/lon using the generic parser logic as a fallback.
            return self._parse_generic(parts)
        except Exception as e:
            self.logger.debug(f"Error parsing APB: {e}")
            return None

    def _parse_zda(self, parts: list) -> Optional[Tuple[float, float]]:
        """Parse ZDA sentence (UTC Date/Time)."""
        try:
            if len(parts) < 5:
                return None
            time_str = parts[1]
            day = parts[2]
            month = parts[3]
            year = parts[4]
            if not (time_str and day and month and year):
                return None
            date_str = f"{year}{month.zfill(2)}{day.zfill(2)}"  # yyyymmdd
            self.last_utc_time = self._parse_nmea_time(time_str, date_str)
            return None  # ZDA does not contain position
        except Exception as e:
            self.logger.debug(f"Error parsing ZDA: {e}")
            return None

    def _parse_nmea_time(self, time_str: str, date_str: str = "") -> Optional[datetime]:
        """Parse NMEA UTC time (hhmmss[.sss]) and optional date (ddmmyy or yyyymmdd) to datetime (UTC)."""
        try:
            if not time_str or len(time_str) < 6:
                return None
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            microsecond = int(float('0.' + time_str.split('.')[1]) * 1e6) if '.' in time_str else 0
            if date_str:
                # Try ddmmyy or yyyymmdd
                if len(date_str) == 6:  # ddmmyy
                    day = int(date_str[0:2])
                    month = int(date_str[2:4])
                    year = 2000 + int(date_str[4:6])
                elif len(date_str) == 8:  # yyyymmdd
                    year = int(date_str[0:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                else:
                    return None
                return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=UTC)
            else:
                # Use today's date (UTC)
                now = datetime.now(UTC)
                return datetime(now.year, now.month, now.day, hour, minute, second, microsecond, tzinfo=UTC)
        except Exception as e:
            self.logger.debug(f"Error parsing NMEA time: {e}")
            return None


class GPSManager:
    """Manages GPS data from various sources."""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.nmea_parser = NMEAParser()
        self.grid_converter = GridConverter(
            precision=config.getint('ADVANCED', 'grid_precision', fallback=4)
        )
        
        self.current_position = None
        self.current_grid = None
        self.last_update = None
        self.gps_source = config.get('GPS', 'gps_source', fallback='network')
        self.update_interval = config.getint('GPS', 'gps_update_interval', fallback=2) * 60  # Convert to seconds
        
        self.running = False
        self.gps_thread = None
        self.sync_system_clock = config.getboolean('GPS', 'sync_system_clock', fallback=False)
        self.last_sync_time = None
        self.sync_threshold_seconds = 2  # Only sync if drift > 2 seconds
        self.sync_min_interval = 60  # Only sync once per minute
        # Privilege check for system clock sync
        if self.sync_system_clock:
            is_admin = False
            try:
                if platform.system() == 'Windows':
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                else:
                    is_admin = (os.geteuid() == 0)
            except Exception as e:
                self.logger.warning(f"Could not determine privilege level: {e}")
            if not is_admin:
                warning_msg = ("WARNING: System clock sync is enabled, but the script is not running with "
                               "administrator/root privileges. Clock sync will fail.\n"
                               "Run this script as Administrator (Windows) or with sudo (Linux) to enable clock sync.")
                print(warning_msg)
                self.logger.info(warning_msg)
    
    def start(self):
        """Start GPS monitoring."""
        self.running = True
        self.gps_thread = threading.Thread(target=self._gps_worker, daemon=True)
        self.gps_thread.start()
        self.logger.info(f"GPS monitoring started with source: {self.gps_source}")
    
    def stop(self):
        """Stop GPS monitoring."""
        self.running = False
        if self.gps_thread and self.gps_thread.is_alive():
            self.gps_thread.join(timeout=5.0)  # Wait up to 5 seconds
            if self.gps_thread.is_alive():
                self.logger.warning("GPS thread did not terminate cleanly")
        self.logger.info("GPS monitoring stopped")
    
    def _gps_worker(self):
        """Main GPS worker thread."""
        while self.running:
            try:
                if self.gps_source == 'network':
                    self._handle_network_gps()
                elif self.gps_source == 'serial':
                    self._handle_serial_gps()
                elif self.gps_source == 'gpsd':
                    self._handle_gpsd_gps()
                
                # Wait for next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"GPS worker error: {e}")
                time.sleep(10)  # Wait before retry
    
    def _handle_network_gps(self):
        """Handle network GPS data with detailed logging and debugging."""
        try:
            ip = self.config.get('GPS_NETWORK', 'gps_ip')
            port = self.config.getint('GPS_NETWORK', 'gps_port')
            protocol = self.config.get('GPS_NETWORK', 'gps_protocol', fallback='tcp')
            timeout = self.config.getint('GPS_NETWORK', 'gps_timeout', fallback=10)
            self.logger.debug(f"Opening network GPS connection to {ip}:{port} via {protocol.upper()}, timeout {timeout}s")
            if protocol.lower() == 'tcp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.connect((ip, port))
            self.logger.info(f"Network GPS connection to {ip}:{port} established.")
            # Read NMEA data
            data = sock.recv(1024).decode('utf-8', errors='ignore')
            self.logger.debug(f"[Network] Raw data received: {repr(data)}")
            sock.close()
            self.logger.debug(f"Network GPS connection to {ip}:{port} closed.")
            # Parse NMEA sentences
            found_valid = False
            for i, line in enumerate(data.split('\n')):
                if line.strip():
                    self.logger.debug(f"[Network] Line {i+1}: {line.strip()}")
                    coords = self.nmea_parser.parse_nmea_sentence(line)
                    if coords:
                        lat, lon = coords
                        self.logger.info(f"[Network] Parsed valid position: lat={lat}, lon={lon}")
                        self._update_position(lat, lon)
                        found_valid = True
                        break
                    else:
                        self.logger.debug(f"[Network] No valid position in line {i+1}.")
            if not found_valid:
                self.logger.warning("[Network] No valid GPS position found in received data.")
        except Exception as e:
            self.logger.error(f"Network GPS error: {e}")
    
    def _handle_serial_gps(self):
        """Handle serial GPS data with detailed logging and debugging."""
        try:
            port = self.config.get('GPS_SERIAL', 'serial_port')
            baud = self.config.getint('GPS_SERIAL', 'serial_baud')
            timeout = self.config.getint('GPS_SERIAL', 'serial_timeout', fallback=5)
            self.logger.debug(f"Opening serial port {port} at {baud} baud, timeout {timeout}s")
            with serial.Serial(port, baud, timeout=timeout) as ser:
                self.logger.info(f"Serial port {port} opened successfully.")
                found_valid = False
                for i in range(10):
                    if not self.running:
                        self.logger.debug("Serial GPS handler stopped by user.")
                        break
                    line = ser.readline().decode('utf-8', errors='ignore')
                    self.logger.debug(f"[Serial] Line {i+1}: {line.strip()}")
                    if line.strip():
                        coords = self.nmea_parser.parse_nmea_sentence(line)
                        if coords:
                            lat, lon = coords
                            self.logger.info(f"[Serial] Parsed valid position: lat={lat}, lon={lon}")
                            self._update_position(lat, lon)
                            found_valid = True
                            break
                        else:
                            self.logger.debug(f"[Serial] No valid position in line {i+1}.")
                if not found_valid:
                    self.logger.warning("[Serial] No valid GPS position found in 10 lines.")
        except Exception as e:
            self.logger.error(f"Serial GPS error: {e}")
    
    def _handle_gpsd_gps(self):
        """Handle GPSD GPS data using direct socket communication."""
        try:
            host = self.config.get('GPS_GPSD', 'gpsd_host', fallback='localhost')
            port = self.config.getint('GPS_GPSD', 'gpsd_port', fallback=2947)
            timeout = self.config.getint('GPS_GPSD', 'gpsd_timeout', fallback=10)
            
            self.logger.debug(f"Connecting to GPSD at {host}:{port}, timeout {timeout}s")
            
            # Create socket connection to GPSD
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            
            # Send version command to get JSON output
            sock.send(b'?VERSION;\n')
            version_response = sock.recv(1024).decode('utf-8', errors='ignore')
            self.logger.debug(f"GPSD version: {version_response.strip()}")
            
            # Send watch command to enable JSON output
            sock.send(b'?WATCH={"enable":true,"json":true};\n')
            watch_response = sock.recv(1024).decode('utf-8', errors='ignore')
            self.logger.debug(f"GPSD watch response: {watch_response.strip()}")
            
            # Set shorter timeout for data reading
            sock.settimeout(2.0)
            
            # Buffer for incomplete JSON lines
            buffer = ""
            found_valid = False
            
            # Try to read GPS data multiple times (similar to serial GPS)
            for attempt in range(10):
                if not self.running:
                    self.logger.debug("GPSD handler stopped by user.")
                    break
                
                try:
                    # Read data from GPSD
                    data = sock.recv(1024).decode('utf-8', errors='ignore')
                    if not data:
                        self.logger.debug(f"[GPSD] No data received on attempt {attempt + 1}")
                        continue
                    
                    self.logger.debug(f"[GPSD] Raw data attempt {attempt + 1}: {repr(data)}")
                    
                    # Add to buffer and process complete lines
                    buffer += data
                    lines = buffer.split('\n')
                    
                    # Keep the last line in buffer (might be incomplete)
                    buffer = lines[-1]
                    
                    # Process complete lines
                    for line in lines[:-1]:
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                gps_data = json.loads(line)
                                self.logger.debug(f"[GPSD] JSON: {gps_data}")
                                
                                # Check if this is a TPV (Time Position Velocity) report
                                if gps_data.get('class') == 'TPV':
                                    lat = gps_data.get('lat')
                                    lon = gps_data.get('lon')
                                    mode = gps_data.get('mode', 0)
                                    
                                    if lat is not None and lon is not None and mode >= 2:  # 2D or 3D fix
                                        self.logger.info(f"[GPSD] Parsed valid position: lat={lat}, lon={lon}, mode={mode}")
                                        self._update_position(lat, lon)
                                        found_valid = True
                                        break
                                    else:
                                        self.logger.debug(f"[GPSD] No valid position in TPV: lat={lat}, lon={lon}, mode={mode}")
                                
                                # Check if this is a SKY (Satellite) report for time sync
                                elif gps_data.get('class') == 'SKY':
                                    time_str = gps_data.get('time')
                                    if time_str:
                                        try:
                                            # Parse GPSD time format (ISO 8601)
                                            gps_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                            self.nmea_parser.last_utc_time = gps_time
                                            self.logger.debug(f"[GPSD] Parsed time: {gps_time}")
                                        except Exception as e:
                                            self.logger.debug(f"[GPSD] Error parsing time {time_str}: {e}")
                            
                            except json.JSONDecodeError as e:
                                self.logger.debug(f"[GPSD] JSON decode error: {e}")
                                continue
                    
                    if found_valid:
                        break
                        
                except socket.timeout:
                    self.logger.debug(f"[GPSD] Timeout on attempt {attempt + 1}")
                    continue
                except Exception as e:
                    self.logger.debug(f"[GPSD] Error on attempt {attempt + 1}: {e}")
                    break
            
            if not found_valid:
                self.logger.warning("[GPSD] No valid GPS position found in 10 attempts.")
            
            sock.close()
            self.logger.debug(f"GPSD connection to {host}:{port} closed")
            
        except Exception as e:
            self.logger.error(f"GPSD error: {e}")
    
    def _process_nmea_sentence(self, sentence: str):
        """Process NMEA sentence and update position."""
        coords = self.nmea_parser.parse_nmea_sentence(sentence)
        if coords:
            lat, lon = coords
            self._update_position(lat, lon)
    
    def _update_position(self, lat: float, lon: float):
        """Update current position and grid square."""
        self.current_position = (lat, lon)
        new_grid = self.grid_converter.lat_lon_to_grid(lat, lon)
        
        if new_grid != self.current_grid:
            old_grid = self.current_grid
            self.current_grid = new_grid
            self.last_update = datetime.now()
            
            self.logger.info(f"Grid square updated: {old_grid} -> {new_grid} (lat: {lat:.6f}, lon: {lon:.6f})")
        
        if self.sync_system_clock:
            gps_time = self.nmea_parser.last_utc_time  # Assume parser stores last UTC time as datetime
            if gps_time:
                now = datetime.now(UTC)
                drift = abs((gps_time - now).total_seconds())
                if (self.last_sync_time is None or (datetime.now(UTC) - self.last_sync_time).total_seconds() > self.sync_min_interval) and drift > self.sync_threshold_seconds:
                    self.logger.info(f"Syncing system clock to GPS time: {gps_time.isoformat()} (drift: {drift:.2f}s)")
                    try:
                        if platform.system() == 'Windows':
                            # Prepare SYSTEMTIME structure
                            class SYSTEMTIME(ctypes.Structure):
                                _fields_ = [
                                    ("wYear", ctypes.c_ushort),
                                    ("wMonth", ctypes.c_ushort),
                                    ("wDayOfWeek", ctypes.c_ushort),
                                    ("wDay", ctypes.c_ushort),
                                    ("wHour", ctypes.c_ushort),
                                    ("wMinute", ctypes.c_ushort),
                                    ("wSecond", ctypes.c_ushort),
                                    ("wMilliseconds", ctypes.c_ushort),
                                ]
                            systime = SYSTEMTIME()
                            systime.wYear = gps_time.year
                            systime.wMonth = gps_time.month
                            systime.wDay = gps_time.day
                            systime.wHour = gps_time.hour
                            systime.wMinute = gps_time.minute
                            systime.wSecond = gps_time.second
                            systime.wMilliseconds = int(gps_time.microsecond / 1000)
                            # Set system time (UTC)
                            if not ctypes.windll.kernel32.SetSystemTime(ctypes.byref(systime)):
                                raise ctypes.WinError()
                        else:
                            # Linux: use date or timedatectl
                            date_str = gps_time.strftime('%Y-%m-%d %H:%M:%S')
                            try:
                                subprocess.run(['sudo', 'date', '-u', '--set', date_str], check=True)
                            except Exception as e:
                                # Try timedatectl as fallback
                                subprocess.run(['sudo', 'timedatectl', 'set-time', date_str], check=True)
                        self.logger.info("System clock successfully synced to GPS time.")
                        self.last_sync_time = datetime.now(UTC)
                    except Exception as e:
                        self.logger.error(f"Failed to sync system clock: {e}")

    def get_current_grid(self) -> Optional[str]:
        """Get current grid square."""
        return self.current_grid

    def get_last_update(self) -> Optional[datetime]:
        """Get timestamp of last grid update."""
        return self.last_update

    def info_and_print(self, msg):
        self.logger.info(msg)
        if not self.config.getboolean('LOGGING', 'debug_mode', fallback=False):
            print(msg)


class ApplicationCommunicator:
    """Handles communication with both WSJT-X and JS8-Call."""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.wsjtx_port = config.getint('APPLICATIONS', 'wsjtx_port', fallback=2237)
        self.js8call_udp_port = config.getint('APPLICATIONS', 'js8call_port', fallback=2242)  # For heartbeat detection
        self.js8call_tcp_port = config.getint('APPLICATIONS', 'js8call_tcp_port', fallback=2442)  # For grid updates
        self.socket = None
        self.wsjtx_id = None
        self.wsjtx_last_grid = None
        self.js8call_last_grid = None
        self.wsjtx_last_addr = None  # Store last WSJT-X address/port
        self.MAGIC_NUMBER = 0xadbccbda
        self.SCHEMA_VERSION = 3  # Updated to match your WSJT-X version
        self.wsjtx_last_packet_time = None  # Track last packet time for WSJT-X
        self.js8call_last_packet_time = None  # Track last packet time for JS8Call
        self.detection_timeout = 30  # seconds
        self.wsjtx_pending_grid_update = False  # Flag to trigger grid update after next packet
        self.pending_grid_value: Optional[str] = None  # Store pending grid value
        
    def start(self):
        """Start communication with both applications."""
        try:
            # Create UDP socket for WSJT-X communication
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)  # Larger buffer
            # Bind to WSJT-X port for listening
            self.socket.bind(('', self.wsjtx_port))
            self.socket.settimeout(2.0)  # Longer timeout
            
            # Create separate socket for JS8-Call heartbeat detection
            self.js8call_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.js8call_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.js8call_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Bind to JS8-Call UDP port for heartbeat detection
            self.js8call_socket.bind(('', self.js8call_udp_port))
            self.js8call_socket.settimeout(2.0)
            
            self.logger.info(f"Application communication started on WSJT-X port {self.wsjtx_port}, JS8-Call UDP port {self.js8call_udp_port} (heartbeat), TCP port {self.js8call_tcp_port} (updates)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start application communication: {e}")
            return False
    
    def stop(self):
        """Stop communication."""
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.socket.close()
            self.socket = None
        
        if hasattr(self, 'js8call_socket') and self.js8call_socket:
            try:
                self.js8call_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.js8call_socket.close()
            self.js8call_socket = None
            
        self.logger.info("Application communication stopped")
    
    def is_wsjtx_process_running(self):
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'wsjtx' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    
    def is_js8call_process_running(self):
        found = False
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and any(n in name.lower() for n in ['js8call', 'js8']):
                    found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        self.logger.debug(f"[ProcessCheck] JS8Call running: {found}")
        return found
    
    def check_heartbeats(self) -> tuple[bool, bool]:
        """Check for heartbeats from both applications."""
        wsjtx_detected = False
        js8call_detected = False
        now = time.time()
        # Check WSJT-X socket
        try:
            if self.socket:
                data, addr = self.socket.recvfrom(1024)
                if len(data) >= 16:
                    try:
                        magic, schema, pkt_type, id_len = struct.unpack('>LLLL', data[:16])
                        if magic == self.MAGIC_NUMBER:
                            packet_info = f"WSJT-X Packet: type={pkt_type}, schema={schema}, from={addr}"
                            if id_len > 0 and len(data) >= 16 + id_len:
                                wsjtx_id = data[16:16+id_len].decode('utf-8')
                                packet_info += f", id={wsjtx_id}"
                            if pkt_type == 0:  # Heartbeat
                                self.logger.debug(f"{packet_info} (Heartbeat)")
                                wsjtx_detected = True
                                self.wsjtx_last_addr = addr
                                self.wsjtx_last_packet_time = now
                                # If a grid update is pending, send it now
                                if self.wsjtx_pending_grid_update:
                                    self._send_pending_wsjtx_grid_update()
                            elif pkt_type == 1:  # Status
                                self.logger.debug(f"{packet_info} (Status)")
                                wsjtx_detected = True
                                self.wsjtx_last_addr = addr
                                self.wsjtx_last_packet_time = now
                                # If a grid update is pending, send it now
                                if self.wsjtx_pending_grid_update:
                                    self._send_pending_wsjtx_grid_update()
                            elif pkt_type == 2:  # Decode
                                self.logger.debug(f"{packet_info} (Decode)")
                            elif pkt_type == 3:  # Clear
                                self.logger.debug(f"{packet_info} (Clear)")
                            elif pkt_type == 4:  # Reply
                                self.logger.debug(f"{packet_info} (Reply)")
                            elif pkt_type == 5:  # QSO Logged
                                self.logger.debug(f"{packet_info} (QSO Logged)")
                            elif pkt_type == 6:  # Close
                                self.logger.debug(f"{packet_info} (Close)")
                            elif pkt_type == 7:  # Replay
                                self.logger.debug(f"{packet_info} (Replay)")
                            elif pkt_type == 8:  # Halt Tx
                                self.logger.debug(f"{packet_info} (Halt Tx)")
                            elif pkt_type == 9:  # Free Text
                                self.logger.debug(f"{packet_info} (Free Text)")
                            elif pkt_type == 10:  # WSPR Decode
                                self.logger.debug(f"{packet_info} (WSPR Decode)")
                            elif pkt_type == 11:  # Location
                                self.logger.debug(f"{packet_info} (Location)")
                            elif pkt_type == 12:  # Logged ADIF
                                self.logger.debug(f"{packet_info} (Logged ADIF)")
                            elif pkt_type == 13:  # Highlight Call
                                self.logger.debug(f"{packet_info} (Highlight Call)")
                            elif pkt_type == 14:  # Switch Configuration
                                self.logger.debug(f"{packet_info} (Switch Configuration)")
                            elif pkt_type == 15:  # Configure
                                self.logger.debug(f"{packet_info} (Configure)")
                            else:
                                self.logger.debug(f"{packet_info} (Unknown type)")
                            
                            if pkt_type == 0 and id_len > 0 and len(data) >= 16 + id_len:
                                self.wsjtx_id = data[16:16+id_len].decode('utf-8')
                    except struct.error as e:
                        self.logger.debug(f"WSJT-X packet parsing error: {e}")
                    except UnicodeDecodeError as e:
                        self.logger.debug(f"WSJT-X packet decode error: {e}")
                else:
                    self.logger.debug(f"WSJT-X short packet received: {len(data)} bytes from {addr}")
        except socket.timeout:
            pass
        except Exception as e:
            self.logger.debug(f"WSJT-X heartbeat check error: {e}")
        # Timeout logic for detection
        if self.wsjtx_last_packet_time is not None and (now - self.wsjtx_last_packet_time) > self.detection_timeout:
            wsjtx_detected = False
        if not self.is_wsjtx_process_running():
            wsjtx_detected = False
        # JS8Call detection is now process-only
        js8call_detected = self.is_js8call_process_running()
        return wsjtx_detected, js8call_detected
    
    def send_wsjtx_grid_update(self, grid: str) -> bool:
        """Send grid square update to WSJT-X using a new UDP socket (let OS choose source port)."""
        if not self.wsjtx_id or not self.wsjtx_last_addr:
            return False
        try:
            # Build location change packet with "GRID:" prefix (like the working sample)
            packet = self._build_wsjtx_location_packet("GRID:" + grid)
            # Create a new UDP socket for sending, do not bind to any port
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.sendto(packet, self.wsjtx_last_addr)
            udp_sock.close()
            self.wsjtx_last_grid = grid
            self.logger.info(f"Sent grid update to WSJT-X: {grid} (to {self.wsjtx_last_addr})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send grid update to WSJT-X: {e}")
            return False
    
    def send_js8call_grid_update(self, grid: str) -> bool:
        """Send grid square update to JS8-Call via TCP."""
        try:
            # Create TCP connection to JS8-Call
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.settimeout(5.0)
            
            # Connect to JS8-Call TCP port
            tcp_sock.connect(('127.0.0.1', self.js8call_tcp_port))
            
            # Build the correct JS8-Call command (confirmed working)
            command = {
                'type': 'STATION.SET_GRID',
                'value': grid
            }
            
            # Send command via TCP
            message = json.dumps(command).encode('utf-8') + b'\n'
            tcp_sock.send(message)
            
            # Wait for response
            try:
                response = tcp_sock.recv(1024)
                if response:
                    self.logger.debug(f"JS8-Call response: {response.decode('utf-8', errors='ignore')}")
            except socket.timeout:
                self.logger.debug("No response from JS8-Call (timeout)")
            
            tcp_sock.close()
            
            self.js8call_last_grid = grid
            self.logger.info(f"Sent grid update to JS8-Call via TCP: {grid}")
            return True
            
        except ConnectionRefusedError:
            self.logger.error("JS8-Call TCP connection refused - check if JS8-Call is running and listening on port 2442")
            return False
        except Exception as e:
            self.logger.error(f"Failed to send grid update to JS8-Call: {e}")
            return False
    
    def _build_wsjtx_location_packet(self, grid: str) -> bytes:
        """Build WSJT-X location change packet using exact py-wsjtx format."""
        # Create packet exactly like py-wsjtx LocationChangePacket.Builder
        packet = bytearray()
        
        # Header (magic + schema) - same as PacketWriter.write_header()
        packet.extend(struct.pack('>L', self.MAGIC_NUMBER))  # Magic
        packet.extend(struct.pack('>L', self.SCHEMA_VERSION))  # Schema
        
        # Packet type (LocationChangePacket = 11)
        packet.extend(struct.pack('>l', 11))  # Note: using 'l' (signed) not 'L' (unsigned)
        
        # WSJT-X ID (QString format)
        id_str = self.wsjtx_id or "WSJT-X"
        id_bytes = id_str.encode('utf-8')
        packet.extend(struct.pack('>l', len(id_bytes)))  # Length as signed int
        packet.extend(id_bytes)
        
        # Grid square (QString format)
        grid_bytes = grid.encode('utf-8')
        packet.extend(struct.pack('>l', len(grid_bytes)))  # Length as signed int
        packet.extend(grid_bytes)
        
        return bytes(packet)
    
    def _send_pending_wsjtx_grid_update(self):
        # Send the pending grid update to WSJT-X after a short delay, only once
        if hasattr(self, 'pending_grid_value') and self.pending_grid_value:
            self.logger.info(f"Preparing to send pending grid update to WSJT-X: {self.pending_grid_value}")
            self.logger.info(f"WSJT-X update will be sent to {self.wsjtx_last_addr} with ID {self.wsjtx_id}")
            time.sleep(2)  # Wait 2 seconds before sending
            self.logger.info(f"Sending pending grid update to WSJT-X: {self.pending_grid_value}")
            self.send_wsjtx_grid_update(self.pending_grid_value)
            self.wsjtx_pending_grid_update = False
            self.pending_grid_value = None


class AutoGrid:
    """Main application class."""
    
    def __init__(self):
        self.config = ConfigManager()
        self.log_manager = LogManager(self.config)
        self.logger = logging.getLogger(__name__)
        
        self.gps_manager = GPSManager(self.config)
        self.app_comm = ApplicationCommunicator(self.config)
        
        self.running = False
        self.wsjtx_detected = False
        self.js8call_detected = False
        # Track previous detection state for restart detection
        self.prev_wsjtx_detected = False
        self.prev_js8call_detected = False
        # Timing settings
        self.heartbeat_interval = self.config.getint('ADVANCED', 'heartbeat_interval', fallback=10)
        self.sleep_interval = self.config.getint('ADVANCED', 'sleep_interval', fallback=5)
        self.retry_interval = self.config.getint('APPLICATIONS', 'retry_interval', fallback=5)
        self.max_retries = self.config.getint('APPLICATIONS', 'max_retries', fallback=3)
    
    def info_and_print(self, msg):
        self.logger.info(msg)
        if not self.config.getboolean('LOGGING', 'debug_mode', fallback=False):
            print(msg)

    def start(self):
        """Start the application."""
        self.info_and_print("Starting WSJT-X/JS8-Call Auto Grid")
        self.info_and_print(f"GPS Source: {self.config.get('GPS', 'gps_source')}")
        
        # Start GPS monitoring
        self.gps_manager.start()
        
        # Start communication
        if not self.app_comm.start():
            self.logger.info("Failed to start application communication")
        
        self.running = True
        self._main_loop()
    
    def stop(self):
        """Stop the application."""
        self.info_and_print("Stopping WSJT-X/JS8-Call Auto Grid")
        self.running = False
        
        self.gps_manager.stop()
        self.app_comm.stop()
    
    def _main_loop(self):
        """Main application loop."""
        while self.running:
            try:
                wsjtx_running, js8call_running = self.app_comm.check_heartbeats()
                # Detect transitions for WSJT-X
                if wsjtx_running and not self.wsjtx_detected:
                    self.info_and_print("WSJT-X detected")
                if not wsjtx_running and self.wsjtx_detected:
                    self.info_and_print("WSJT-X no longer detected")
                # Detect transitions for JS8Call
                if js8call_running and not self.js8call_detected:
                    self.info_and_print("JS8-Call detected")
                if not js8call_running and self.js8call_detected:
                    self.info_and_print("JS8-Call no longer detected")
                # Immediately send grid update if either app was just (re)detected
                current_grid = self.gps_manager.get_current_grid()
                if current_grid:
                    if wsjtx_running and not self.prev_wsjtx_detected:
                        # Instead of sending immediately, set a pending flag
                        self.app_comm.wsjtx_pending_grid_update = True
                        self.app_comm.pending_grid_value = current_grid
                    if js8call_running and not self.prev_js8call_detected:
                        self._send_js8call_grid_update_with_retry(current_grid)
                # Update detection state
                self.prev_wsjtx_detected = wsjtx_running
                self.prev_js8call_detected = js8call_running
                self.wsjtx_detected = wsjtx_running
                self.js8call_detected = js8call_running
                # Update grid squares if needed (normal logic)
                self._update_grid_squares()
                # Sleep based on application status
                if self.wsjtx_detected or self.js8call_detected:
                    time.sleep(self.heartbeat_interval)
                else:
                    time.sleep(self.sleep_interval)
            except KeyboardInterrupt:
                self.info_and_print("Received interrupt signal")
                break
            except Exception as e:
                self.logger.info(f"Main loop error: {e}")
                time.sleep(self.retry_interval)
    
    def _update_grid_squares(self):
        """Update grid squares in detected applications."""
        current_grid = self.gps_manager.get_current_grid()
        if not current_grid:
            return
        
        # Check if grid has changed for WSJT-X
        if (self.wsjtx_detected and 
            current_grid != self.app_comm.wsjtx_last_grid):
            self._send_wsjtx_grid_update_with_retry(current_grid)
        
        # Check if grid has changed for JS8-Call
        if (self.js8call_detected and 
            current_grid != self.app_comm.js8call_last_grid):
            self._send_js8call_grid_update_with_retry(current_grid)
    
    def _send_wsjtx_grid_update_with_retry(self, grid: str):
        """Send WSJT-X grid update with retry mechanism."""
        for attempt in range(self.max_retries):
            if self.app_comm.send_wsjtx_grid_update(grid):
                return
            else:
                self.logger.info(f"WSJT-X grid update attempt {attempt + 1} failed")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
        
        self.logger.info(f"Failed to send WSJT-X grid update after {self.max_retries} attempts")
    
    def _send_js8call_grid_update_with_retry(self, grid: str):
        """Send JS8-Call grid update with retry mechanism."""
        for attempt in range(self.max_retries):
            if self.app_comm.send_js8call_grid_update(grid):
                return
            else:
                self.logger.info(f"JS8-Call grid update attempt {attempt + 1} failed")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
        
        self.logger.info(f"Failed to send JS8-Call grid update after {self.max_retries} attempts")


def main():
    """Main entry point."""
    app = None
    try:
        app = AutoGrid()
        app.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        if app:
            try:
                app.stop()
            except Exception as e:
                print(f"Error during shutdown: {e}")


if __name__ == "__main__":
    main() 