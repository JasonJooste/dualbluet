# dualbluet
A script for syncronising bluetooth keys for dual boot systems.

Bluetooth devices share a secret key for authentiction that is matched to the device's MAC address. Normally, this is totally fine, but when dual booting the MAC address is the same for both OSs and they establish two different keys with the device and the device only remembers the most recent device. This script syncs the keys across both devices. 

# Steps
1. Connect to all bluetooth devices from Linux
2. Connect to all bluetooth devices from Windows
3. Run dualbluet, which will take all of the correct keys 
