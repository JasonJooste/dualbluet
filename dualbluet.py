#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

CHNTPW_LIST_COMMAND = "ls \{}\Services\BTHPORT\Parameters\Keys\{}\nq" # The q quits after the information is gathered
CHNTPW_KEY_COMMAND = 'hex \{}\Services\BTHPORT\Parameters\Keys\{}\{}\nq'


def execute_chntpw(command):
    """
    Execute a command in chntpw
    """
    p_in = subprocess.Popen(["echo", command], stdout=subprocess.PIPE)
    p1 = subprocess.Popen(["chntpw", "-e", "SYSTEM"], stdin=p_in.stdout, stdout=subprocess.PIPE)
    return str(p1.communicate()[0])


def get_control_name():
    """Determine whether this system stores the keys under currentcontrolset or controlset001"""
    match_001 = "not found" not in execute_chntpw("ls \ControlSet001\nq")
    match_current = "not found" not in execute_chntpw("ls \CurrentControlSet\nq")
    assert not match_current and match_001, "The control set entries are mutually exclusive"
    if match_001:
        return "ControlSet001"
    else:
        return "CurrentControlSet"


def access_registry(registry_file, device):
    """Access the windows registry with chntpw and retrieve the bluetooth passwords"""
    assert ":" not in device, "The device address should be in windows format"
    os.chdir(registry_file)
    control_name = get_control_name()

    # Execute the command to get the bluetooth keys
    chntpw_output = execute_chntpw(CHNTPW_LIST_COMMAND.format(control_name, device))
    if "not found" in chntpw_output:
        print(f"Error: \n{chntpw_output}")
        raise RuntimeError("Could not move to directory")
    # Extract the bluetooth keys from the output
    device_codes = re.findall(r'<(.*?)>', chntpw_output)
    # The keys are all 12 characters long
    device_codes = [key for key in device_codes if len(key) == 12]
    # Now get the passwords for those keys
    passwords = []
    # NOTE: This could be improved here
    for key in device_codes:
        chntpw_output = execute_chntpw(CHNTPW_KEY_COMMAND.format(control_name, device, key))
        split_output = chntpw_output.split("00000  ")
        pw = "".join(split_output[1][:47].lower().split())
        passwords.append(pw)
    # Format the keys in the ubuntu style
    device_codes = [":".join([key[i:i + 2].upper() for i in range(0, len(key), 2)]) for key in device_codes]
    return device_codes, passwords


def get_ubuntu_bluetooth(device):
    """ Get a list of the attached bluetooth devices on the ubuntu machine"""
    # Execute the command to get the bluetooth keys
    p = f"/var/lib/bluetooth/{device}"
    subdirs = Path(p).iterdir()
    try:
        bluetooth_keys = list(p.stem for p in subdirs)
    except PermissionError:
        sys.exit("Try running the script again with root privileges, i.e. sudo dualbluet")
    # The keys are all 12 characters long
    bluetooth_keys = [key for key in bluetooth_keys if len(key) == 17]
    return bluetooth_keys


def replace_key(device, key, pw):
    """Replace the existing key for the linux device with the windows key"""
    filepath = Path(f"/var/lib/bluetooth/{device}/{key}/info")
    with filepath.open("r+") as f:
        text = f.read()
        # Now replace the existing text with the new password
        text = re.sub(r"\[LinkKey]\nKey=\S*", r"[LinkKey]\nKey=" + pw.upper(), text)
        # Rewrite with the new key
        f.seek(0)
        f.write(text)
        f.truncate()


def sync_all_devices(windows_mount_point, local_bt_device):
    """ Find the windows keys for all paired linux devices and replace the keys with the windows keys"""
    # Get all of the connected ubuntu devices - by path is fine for now
    ubuntu_ext_devices = get_ubuntu_bluetooth(local_bt_device)
    registry_location = Path(windows_mount_point) / "Windows" / "System32" / "config"
    print(f"Registry location should be: {registry_location}")
    assert registry_location.exists(), "Registry location should exist"
    windows_ext_devices, windows_passwords = access_registry(registry_location, linux_to_windows(local_bt_device))
    # Convert to linux format
    overlapping_keys = [(key, pw) for key, pw in zip(windows_ext_devices, windows_passwords) if
                        key in ubuntu_ext_devices]
    for ext_device, key in overlapping_keys:
        if ext_device in ubuntu_ext_devices:
            print(f"Device: {ext_device}, Key: {key}")
            print(f"Replacing key for bluetooth device with MAC address {ext_device}")
            replace_key(local_bt_device, ext_device, key)
    # Restart the bluetooth service
    os.system("systemctl restart bluetooth")


def windows_to_linux(device_code):
    return ":".join([device_code[i:i + 2] for i in range(0, len(device_code), 2)]).upper()


def linux_to_windows(device_code):
    return device_code.lower().replace(":", "")


def find_windows_partition():
    possible_locations = ["/mnt/", f"/media/{os.getlogin()}/"]
    partitions = []
    for location in possible_locations:
        partitions.extend(Path(location).glob("*"))
    windows_partition = None
    for partition in partitions:
        if (partition / "Windows" / "System32" / "config").exists():
            if windows_partition is None:
                windows_partition = partition
            else:
                raise NotImplementedError("Cannot handle multiple windows partitions")
    if windows_partition is None:
        sys.exit("No windows partition found. Try providing it explicitly with the --path argument")
    print(f"Local Windows partition discovered under: {partition}")
    return partition

def find_local_device():
    bt_path = Path("/var/lib/bluetooth")
    local_bt_device = list(bt_path.glob("*:*"))
    if len(local_bt_device) > 1:
        sys.exit(
            "Can't handle multiple bluetooth devices at the moment. Try providing the desired device address "
            "explicitly with the --device variable")
    local_bt_device = local_bt_device[0].stem
    print(f"Local bluetooth device discovered: {local_bt_device}")

    return local_bt_device

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Syncronise bluetooth keys from windows to ubuntu")
    parser.add_argument("-p", "--path", help="Path to the windows mount", required=False)
    parser.add_argument("-d", "--device", help="The address of the bluetooth device", required=False)
    argv = parser.parse_args()
    if argv.path is None:
        path = find_windows_partition()
    else:
        path = argv.path
    if argv.device is None:
        device = find_local_device()
    else:
        device = argv.device
    sync_all_devices(path, device)

# Note: Could refactor names to MAC
