# dualbluet
A script for syncronising bluetooth keys for dual boot systems.

Bluetooth devices share a secret key for authentiction that is matched to the device's MAC address. Normally, this is totally fine, but when dual booting the MAC address is the same for both OSs and they establish two different keys with the device and the device only remembers the most recent key. This script syncs the keys across both devices. 

# Steps
1. Connect to all bluetooth devices from Linux
2. Connect to all bluetooth devices from Windows
3. Run dualbluet as root (`sudo ./dualbluet.py`), which will copy the correct keys from Windows over to Linux

I've only tested this script on my own device so there's almost certainly going to be bugs on other people's systems. Let me know if it doesn't work for you and maybe we can figure it out!
