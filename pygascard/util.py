"""Utilities for manipulating data from gascard devices.

Author: Grayson Bellamy
Date: 2024-05-03
"""

import glob
from comm import SerialDevice
from device import Gascard
from trio import run
import trio
import re
from typing import Any


def gas_correction():
    """Calculates the gas correction factor for the gascard device.

    Returns:
    -------
    float
        The gas correction factor.
    """
    pass


async def find_devices():
    """Finds all connected gascard devices.

    Find all available serial ports using the `ls` command
    Iterate through all possible baud rates

    If there is an gascard device on that port (copy code form new_device that checks )
        get what device is
    add to dictionary with port name and type of device on port (if no device, don't add to dictionary)
    return dictionary


    Returns:
    -------
    list
        A list of all connected gascard devices.
    """
    # Get the list of available serial ports
    result = glob.glob("/dev/ttyUSB*")

    # Iterate through the output and check for gascard devices
    devices = {}
    for port in result:
        # Check if the port is an gascard device
        dev = await is_gascard_device(port)
        if dev:
            devices.update({port: dev[1]})
    return devices


async def is_gascard_device(port, id: str = "A", **kwargs: Any):
    """Check if the given port is an gascard device.

    Parameters:
    ----------
    port : str
        The name of the serial port.

    Returns:
    -------
    bool
        True if the port is an gascard device, False otherwise.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info_raw = await device._write_readline("X")
    if not dev_info_raw:
        return False
    X_labels = [
        "Mode",
        "Firmware Version",
        "Serial Number",
        "Config Register",
        "Frequency",
        "Time Constant",
        "Switches State",
    ]
    dev_info_raw = dev_info_raw.replace("\x00", "")
    dev_info = dict(zip(X_labels, dev_info_raw.split()))
    if dev_info.get("Serial Number", ""):
        return (True, "Gascard")
    return False


def get_device_type(port):
    """Get the device type for the given port.

    Parameters:
    ----------
    port : str
        The name of the serial port.

    Returns:
    -------
    dict
        A dictionary containing the port name and the type of device on the port.
    """
    # Implement the logic to get the device information
    # You can use any method that suits your needs
    pass
