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
import daq


def gas_correction():
    """Calculates the gas correction factor for the gascard device.

    Returns:
        float: The gas correction factor.
    """
    pass


async def find_devices() -> list[str]:
    """Finds all connected gascard devices.

    Returns:
        list[str]: A list of all connected gascard devices.
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


async def is_gascard_device(port: str, **kwargs: Any) -> bool:
    """Check if the given port is an gascard device.

    Parameters:
        port (str): The name of the serial port.
        id (str): The device ID. Default is "A".

    Returns:
        bool: True if the port is an gascard device, False otherwise.
    """
    acc_gas = ["CO", "CO2", "CH4"]
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info_raw = await device._write_readline("U")
    if not dev_info_raw:
        return False
    U_labels = ["Mode", "Gas Range", "Gas Type", "Background Gas", "Display selection"]
    dev_info_raw = dev_info_raw.replace("\x00", "")
    dev_info = dict(zip(U_labels, dev_info_raw.split()))
    if dev_info.get("Gas Type", "") in acc_gas:
        return (True, "Gascard")
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
    get_code2 = "Zero Pot"
    set_code = "Time Constant"
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
    await Daq.time_const((temp["B"][set_code] + 1))
    print(f"Get data: {await Daq.get([set_code])}")
    await Daq.time_const((temp["B"][set_code]))
    print(f"Get data: {await Daq.get([set_code])}")
