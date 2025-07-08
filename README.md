# WSJT-X/JS8-Call Auto Grid Square Updater

Automatically updates your grid square location in WSJT-X and JS8-Call based on GPS data. This program monitors your GPS position and automatically sends grid square updates to both applications when they start or when your location changes.

## Features

- **Multiple GPS Sources**: Supports serial GPS devices, network GPS (TCP/UDP), and GPSD (Linux)
- **Universal NMEA Support**: Works with all NMEA sentence types, not just GPGLL/GPGGA
- **Dual Application Support**: Automatically detects and updates both WSJT-X and JS8-Call
- **Cross-Platform**: Works on Windows XP+ and Linux
- **Lightweight**: Minimal resource usage, designed as a companion application
- **GridTracker Compatible**: Releases control after updates to allow GridTracker to run
- **Extensive Logging**: Detailed logs for troubleshooting and monitoring
- **Easy Configuration**: Simple INI file configuration with detailed comments
- **Optional System Clock Sync**: Can set your computer's clock to GPS time (Windows & Linux, admin/root required)

## Quick Start

### Prerequisites

- Python 3.6 or newer
- GPS device (serial, network, or GPSD)
- WSJT-X and/or JS8-Call installed and configured for UDP reporting

### Installation

1. **Download the program** to a folder on your computer
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Edit the configuration file** (`config.ini`) to match your GPS setup
4. **Run the program**:
   ```bash
   python autogrid.py
   ```

## Configuration

The program uses a `config.ini` file for all settings. Open this file in any text editor to configure your setup.

### GPS Configuration

#### GPS Source Type
Choose your GPS source in the `[GPS]` section:

```ini
# For network GPS devices (most common)
gps_source = network

# For USB/serial GPS devices
gps_source = serial

# For GPSD on Linux systems
gps_source = gpsd
```

#### Network GPS Setup
If using network GPS, configure in `[GPS_NETWORK]`:

```ini
# Your GPS device's IP address
gps_ip = 192.168.1.100

# Your GPS device's port (usually 11010)
gps_port = 11010

# Protocol: tcp or udp (most devices use tcp)
gps_protocol = tcp
```

#### Serial GPS Setup
If using serial GPS, configure in `[GPS_SERIAL]`:

```ini
# Windows: COM1, COM2, COM3, etc.
# Linux: /dev/ttyUSB0, /dev/ttyACM0, etc.
serial_port = COM7

# Baud rate (check your GPS manual)
serial_baud = 9600
```

#### GPSD Setup (Linux Only)
If using GPSD on Linux, configure in `[GPS_GPSD]`:

```ini
# Usually localhost for local GPSD
gpsd_host = localhost

# Default GPSD port
gpsd_port = 2947
```

#### System Clock Sync
If you want the program to set your computer's clock to GPS time, enable this in the `[GPS]` section:

```ini
# Set your computer's clock to GPS time (requires admin/root)
sync_system_clock = true
```

- On **Windows**, the script must be run as Administrator.
- On **Linux**, the script must be run with `sudo` or as root.
- The clock will only be set if the GPS fix is valid and the time is recent.
- The script will not set the clock more than once per minute, and only if the drift is greater than 2 seconds.

### Application Settings

The program automatically detects WSJT-X and JS8-Call. You can configure ports if you've changed the defaults:

```ini
# WSJT-X UDP port (default: 2237)
wsjtx_port = 2237

# JS8-Call UDP port (default: 2242)
# Used for heartbeat detection only
js8call_port = 2242

# JS8-Call TCP port (default: 2442)
# Used for grid updates
js8call_tcp_port = 2442
```

### Logging Settings

Control logging behavior in `[LOGGING]`:

```ini
# Enable console output for debugging
debug_mode = false

# Log detail level: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = INFO

# Number of log files to keep (older files are automatically deleted)
keep_logs = 5
```

## How It Works

1. **GPS Monitoring**: The program continuously monitors your GPS position
2. **Application Detection**: Automatically detects when WSJT-X or JS8-Call starts
3. **Grid Calculation**: Converts GPS coordinates to Maidenhead grid squares
4. **Automatic Updates**: Sends grid updates to applications when they start or when location changes
5. **Background Operation**: Runs quietly in the background, using minimal resources

## GPS Setup Guide

### Network GPS (Recommended)

Most modern GPS devices support network connectivity:

1. **Connect your GPS device** to your network
2. **Find the IP address** of your GPS device (check device manual or router settings)
3. **Configure the program** with the GPS device's IP and port
4. **Test the connection** by running the program with debug mode enabled

### Serial GPS

For USB or serial GPS devices:

1. **Connect your GPS device** via USB or serial cable
2. **Find the correct port name**:
   - Windows: Check Device Manager for COM ports
   - Linux: Usually `/dev/ttyUSB0` or `/dev/ttyACM0`
3. **Set the correct baud rate** (check your GPS manual)
4. **Test the connection** with debug mode enabled

### GPSD (Linux Only)

For Linux systems with GPSD:

1. **Install GPSD**: `sudo apt-get install gpsd` (Ubuntu/Debian)
2. **Start GPSD**: `sudo systemctl start gpsd`
3. **Enable GPSD**: `sudo systemctl enable gpsd`
4. **Configure the program** to use GPSD source
5. **No additional Python modules required** - GPSD support is built-in

## Troubleshooting

### Common Issues

#### "Configuration file not found"
- Make sure `config.ini` is in the same folder as `autogrid.py`
- Check that the file name is exactly `config.ini` (not `config.ini.txt`)

#### "GPS connection failed"
- Verify your GPS device is powered on and connected
- Check IP address and port for network GPS
- Check COM port and baud rate for serial GPS
- Enable debug mode to see detailed error messages

#### "No applications detected"
- Make sure WSJT-X or JS8-Call is running
- Check that UDP reporting is enabled in the applications
- Verify the UDP ports match in both the program and applications

#### "Grid square not updating"
- Check that your GPS has a valid fix (satellite lock)
- Enable debug mode to see GPS data being received
- Verify the applications are receiving the updates

### Debug Mode

Enable debug mode to see detailed information:

1. **Edit config.ini** and set `debug_mode = true`
2. **Run the program** and watch the console output
3. **Check the log files** in the `logs` folder for detailed information

### Log Files

Log files are stored in the `logs` folder with timestamps:
- `autogrid_YYYYMMDD_HHMMSS.log`
- Old log files are automatically deleted (keeps 5 by default)
- Check log files for detailed error information

### System Clock Sync Issues
- **Permission denied**: Make sure you run the script as Administrator (Windows) or with `sudo` (Linux).
- **Clock not changing**: Check the logs for errors. Some systems may require additional permissions or configuration to allow time changes.
- **Verifying**: After running, check your system clock and the log file for confirmation of successful sync.

## Advanced Configuration

### Grid Square Precision

Control grid square precision in `[ADVANCED]`:

```ini
# 4-character grid (e.g., FN31) - Most common
grid_precision = 4

# 6-character grid (e.g., FN31ab) - More precise
grid_precision = 6
```

### Update Intervals

Control how often the program checks for updates:

```ini
# GPS update interval (minutes)
gps_update_interval = 2

# Application heartbeat check interval (seconds)
heartbeat_interval = 10

# Sleep interval when no applications detected (seconds)
sleep_interval = 5
```

## File Structure

```
wsjtx-js8call-autogrid/
├── autogrid.py          # Main program
├── config.ini           # Configuration file
├── requirements.txt     # Python dependencies
├── setup.py            # Installation script
├── README.md           # This file
└── logs/               # Log files (created automatically)
    ├── autogrid_20231201_120000.log
    └── ...
```

## Dependencies

- **pyserial**: Serial communication for GPS devices
- **psutil**: Process detection for Linux and Windows

## Installation Methods

### Method 1: Direct Python Script
```bash
# Download and extract the program
cd wsjtx-js8call-autogrid
pip install -r requirements.txt
python autogrid.py
```

### Method 2: Install as Package
```bash
# Install the program as a Python package
pip install -e .
autogrid
```



## Support

For issues and questions:

1. **Check the log files** in the `logs` folder
2. **Enable debug mode** and check console output
3. **Verify your configuration** matches your GPS setup
4. **Test with a simple GPS simulator** if available

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## Version History

- **v1.0.0**: Initial release with support for WSJT-X and JS8-Call 