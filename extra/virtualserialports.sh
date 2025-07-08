#!/bin/bash

#Creates linked pairs of virtual serial ports for GPS output
socat pty,link=/dev/ttyGPS-Input,raw,echo=0 pty,link=/dev/ttyGPS-Output,raw,echo=0 &

#wait 15 seconds after creation of virtual serial ports before making changes to permissions or injecting data
sleep 15

#Change group ownership of created virtual serial ports from tty to dialout
chgrp dialout /dev/ttyGPS-Input
chgrp dialout /dev/ttyGPS-Output

#Change group file access permissions from no-r/w to r/w
chmod g+rw /dev/ttyGPS-Input
chmod g+rw /dev/ttyGPS-Output

#use gpspipe to send NMEA data from GPSD to input side of virtual serial ports
gpspipe -d -r -o /dev/ttyGPS-Input
