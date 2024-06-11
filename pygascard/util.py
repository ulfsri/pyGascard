"""Utilities for manipulating data from gascard devices.

Author: Grayson Bellamy
Date: 2024-05-03
"""

import glob
import re
from typing import Any

import anyio
from anyio import create_task_group, run

from . import daq, device
from .comm import SerialDevice


def gas_correction():
    """Calculates the gas correction factor for the gascard device.

    Returns:
        float: The gas correction factor.
    """
    pass


async def update_dict_dev(devices, port) -> dict[str, dict[str, str | float]]:
    """Updates the dictionary with the new values.

    Args:
        devices (dict): The dictionary of devices.
        port (str): The name of the serial port.

    Returns:
        dict: The dictionary of devices with the updated values.
    """
    dev = await is_gascard_device(port)
    if dev:
        devices.update({port: dev[1]})
    return devices


async def find_devices() -> dict[str, device.Gascard]:
    """Finds all connected gascard devices.

    Returns:
        dict[str, device.Gascard]: A dictionary of all connected Gascard devices. Port:Object
    """
    # Get the list of available serial ports
    result = glob.glob("/dev/ttyUSB*")

    # Iterate through the output and check for gascard devices
    devices = {}
    async with create_task_group() as g:
        for port in result:
            g.start_soon(update_dict_dev, devices, port)
    return devices


async def is_gascard_device(
    port: str, **kwargs: Any
) -> bool | tuple[bool, device.Gascard]:
    """Check if the given port is an gascard device.

    Parameters:
        port (str): The name of the serial port.
        **kwargs: Any additional keyword arguments.

    Returns:
        bool: True if the port is an gascard device, False otherwise.
        device.Gascard: The gascard device object.
    """
    try:
        return (True, await device.Gascard.new_device(port, **kwargs))
    except ValueError:
        return False


def get_device_type(port):
    """Get the device type for the given port.

    Parameters:
        port (str): The name of the serial port.

    Returns:
        dict[str, str]: A dictionary containing the port name and the type of device on the port.
    """
    # Implement the logic to get the device information
    # You can use any method that suits your needs
    pass


async def diagnose():
    """Run various functions to ensure the device is functioning properly."""
    get_code1 = "Temperature"
    get_code2 = "Zero_Pot"
    set_code = "Time_Constant"
    devs = await find_devices()
    print(f"Devices: {devs}")
    Daq = await daq.DAQ.init({"A": list(devs.keys())[0]})
    print(f"Initiate DAQ with A: {await Daq.dev_list()}")
    await Daq.add_device({"B": list(devs.keys())[1]})
    print(f"Add device B: {await Daq.dev_list()}")
    print(f"Get data (list): {await Daq.get([get_code1, get_code2])}")
    temp = await Daq.get(set_code, "B")
    print(f"Get Data (id, no list): Temp = {temp}")
    await Daq.remove_device(["A"])
    print(f"Remove device A: {await Daq.dev_list()}")
    print(f"Set data (with id).")
    await Daq.set({set_code: (temp["B"][set_code] + 1)}, "B")
    print(f"Get data: {await Daq.get([set_code])}")
    print(f"Set data (without id).")
    await Daq.set({set_code: temp["B"][set_code]})
    print(f"Get data: {await Daq.get([set_code])}")
    await Daq.add_device({"C": list(devs.keys())[0]})
    print(f"Add device C: {await Daq.dev_list()}")
    print(f"Convenience Function.")
    await Daq.time_const(temp["B"][set_code] + 1)
    print(f"Get data: {await Daq.get([set_code])}")
    await Daq.time_const(temp["B"][set_code])
    print(f"Get data: {await Daq.get([set_code])}")
