# Development Documentation

This document contains development-specific information for the WSJT-X/JS8-Call Auto Grid Square Updater.

## Development Dependencies

### Core Dependencies
- **pyserial>=3.5**: Serial communication for GPS devices
- **psutil**: Process detection for Linux and Windows
- **configparser**: Configuration file parsing (built-in Python module)

### Development Tools
- **pyinstaller>=4.0**: For creating Windows executables
- **gpsd-py3>=0.3.0**: Alternative GPSD client (replaced with built-in implementation)

## Building Executables

### Windows Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Create standalone executable
pyinstaller --onefile autogrid.py

# The executable will be created in dist/autogrid.exe
```

### Linux Executable
```bash
# Install PyInstaller
pip install pyinstaller

# Create standalone executable
pyinstaller --onefile autogrid.py

# The executable will be created in dist/autogrid
```

## GPSD Implementation

The GPSD support was refactored to use direct socket communication instead of the `gpsd-py3` module to eliminate the need for virtual environments.

### Protocol Details
- **Port**: 2947 (default GPSD port)
- **Protocol**: TCP socket communication
- **Commands**:
  - `?VERSION;` - Get GPSD version
  - `?WATCH={"enable":true,"json":true};` - Enable JSON output
- **Data Format**: JSON responses
  - TPV (Time Position Velocity) reports for GPS coordinates
  - SKY (Satellite) reports for time synchronization

### Implementation Location
- **File**: `autogrid.py`
- **Method**: `GPSManager._handle_gpsd_gps()`
- **Lines**: ~682-750

## Testing

### GPSD Test Script
A test script is available at `test/test_gpsd.py` to verify GPSD connectivity and data parsing.

```bash
python test/test_gpsd.py
```

### Test Files
- `test/js8call.py` - JS8-Call test utilities
- `test/udp-listener.py` - UDP listener for testing
- `test/wsjtx.py` - WSJT-X test utilities

## Code Structure

### Main Classes
1. **ConfigManager** - Configuration file handling
2. **LogManager** - Logging setup and rotation
3. **GridConverter** - Maidenhead grid square conversion
4. **NMEAParser** - NMEA sentence parsing
5. **GPSManager** - GPS data handling from multiple sources
6. **ApplicationCommunicator** - WSJT-X/JS8-Call communication
7. **AutoGrid** - Main application logic

### GPS Sources Supported
1. **Network** - TCP/UDP GPS data
2. **Serial** - Direct serial port GPS
3. **GPSD** - GPSD daemon (Linux)

## Configuration

### Configuration File
- **File**: `config.ini`
- **Format**: INI format
- **Sections**:
  - `[GPS]` - GPS source configuration
  - `[GPS_NETWORK]` - Network GPS settings
  - `[GPS_SERIAL]` - Serial GPS settings
  - `[GPS_GPSD]` - GPSD settings
  - `[APPLICATIONS]` - WSJT-X/JS8-Call settings
  - `[LOGGING]` - Logging configuration
  - `[ADVANCED]` - Advanced settings

## Development Notes

### Recent Changes
1. **Removed gpsd-py3 dependency** - Replaced with direct socket communication
2. **Simplified requirements.txt** - Only runtime dependencies included
3. **Enhanced GPSD support** - Better error handling and logging

### Future Enhancements
1. **Additional GPS sources** - Support for more GPS input methods
2. **Enhanced logging** - More detailed debugging information
3. **Configuration validation** - Better error checking for configuration

## Troubleshooting Development Issues

### Common Development Problems
1. **Import errors** - Check that all dependencies are installed
2. **GPSD connection issues** - Verify GPSD is running and accessible
3. **Serial port access** - Check permissions on Linux systems
4. **Network GPS timeouts** - Verify network connectivity and firewall settings

### Debug Mode
Enable debug mode in `config.ini`:
```ini
[LOGGING]
debug_mode = true
log_level = DEBUG
```

## Version Control

### Git Workflow
1. **Feature branches** - Create branches for new features
2. **Testing** - Test all GPS sources before committing
3. **Documentation** - Update README.md for user-facing changes
4. **Requirements** - Keep requirements.txt minimal for end users

### Release Process
1. **Version bump** - Update version in setup.py and documentation
2. **Testing** - Test on both Windows and Linux
3. **Documentation** - Update README.md and development.md
4. **Tag release** - Create git tag for release 