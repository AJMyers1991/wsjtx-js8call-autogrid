I have found that some users need even more options for gps inputs so i have included two extra shell scripts for linux users in /extra/

The first is gpsdtotcp.sh - You can run this file as sudo and gpspipe will take the JSON location data provided by GPSD and output to TCP port 11011.  You can then configure the autogrid script (or anything else, really) to use network as gps source, tcp for the protocol, and 11011 for the port number.

The second is virtualserialports.sh - You can run this file as sudo and it will use socat create a pair of linked virutal serial ports in /dev/ called ttyGPS-Input and ttyGPS-Output.  It will then change the group ownership to dialout and make them read/writeable.  Finally, it will use gpspipe to take gpsd's output data and send it into ttyGPS-Input.  You could then configure the autogrid script (or again, anything else) to use serial as gps source, serial_port to /dev/ttyGPS-Output , and serial_baud to 9600 .  This will essentially let you use programs that require a direct serial port connection with your gps source device while gpsd is still connected and functioning.

As with any executable file on linux, copy these to whichever directory you will be running them from and use "chmod +x filename.extension" to make them executable.

You can take either or both of these files and use systemd or whatever tool of choice to have your OS run them at boot.  If you find yourself using them often, its worth it.