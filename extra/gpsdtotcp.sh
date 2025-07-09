#!/bin/bash

#use gpspipe to send NMEA data from GPSD to TCP port (accessible at 127.0.0.1:11011)
gpspipe -r | nc -l -p 11011 &