from typing import Any

import json
import re
from abc import ABC

from comm import SerialDevice
import trio
from trio import run

with open("codes.json") as f:
    codes = json.load(f)
N_labels = codes["N_labels"]
N1_labels = codes["N1_labels"]
C1_labels = codes["C1_labels"]
E1_labels = codes["E1_labels"]
O1_labels = codes["O1_labels"]
X_labels = codes["X_labels"]
U_labels = codes["U_labels"]
values = {
    "N": [N_labels, ["", "", "", "", "", "", "", "", ""]],
    "N1": [N1_labels, ["", "", "", "o", "", "", ""]],
    "C1": [C1_labels, ["", "h", "i", "j", "k", "z", "s", "", "", "p", "p"]],
    "E1": [E1_labels, ["", "", "", "m", "x", "c", "d", "e", "g", "z", "s"]],
    "O1": [O1_labels, ["", "m", "x", "", "a", "b", ""]],
    "X": [X_labels, ["", "", "", "", "f", "t", ""]],
    "U": [U_labels, ["", "", "", "", "d"]],
}


async def new_device(port: str, **kwargs: Any):
    """Creates a new device. Chooses appropriate device based on characteristics.

    Args:
        port (str): The port of the device.
        **kwargs: Any

    Returns:
        Device: The new device.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info_raw = await device._write_readline("U")
    dev_info_raw = dev_info_raw.replace("\x00", "")
    dev_info = dict(zip(U_labels, dev_info_raw.split()))
    if "U" not in dev_info_raw.split()[0]:
        print("Error: Gas Card Not in User Interface Mode")
    return Gascard(device, dev_info, **kwargs)


class Gascard(ABC):
    """Gascard class."""

    def __init__(self, device: SerialDevice, dev_info: dict, **kwargs: Any) -> None:
        """Initialize the Gascard object.

        Args:
            device (SerialDevice): The serial device object.
            dev_info (dict): The device information dictionary.
            **kwargs: Additional keyword arguments.
        """
        self._device = device
        self._dev_info = dev_info
        self._current_mode = "U"
        self._modes = [
            "N",
            "N1",
            #    "C",
            "C1",
            "E1",
            "O1",
            "D",
            "X",
            "U",
        ]  # What is mode C?

        self.N_labels = N_labels
        self.N1_labels = N1_labels
        self.C1_labels = C1_labels
        self.E1_labels = E1_labels
        self.O1_labels = O1_labels
        self.X_labels = X_labels
        self.U_labels = U_labels
        self.values = values

    async def get_mode(self) -> str:
        """Gets the current mode of the device.

        Returns:
            str: Current mode of device
        """
        ret = await self._device._readline()
        mode = ret[0:2].strip()
        if mode in self._modes:
            self.current_mode = mode
        else:
            print("Error: Invalid Mode")
        return mode

    async def set_mode(self, mode: str) -> None:
        """Sets the mode of the device.

        Args:
            mode (str): Desired mode for device
        """
        if mode in self._modes:
            await self._device._write(mode)
            self._current_mode = mode
        else:
            print("Error: Invalid Mode")
        return

    async def get_val(self) -> dict:
        """Gets the current value of the device.

        Returns:
            dict: Normal (N) mode dataframe
        """
        if self._current_mode != "N":
            await self.set_mode("N")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "N" not in df[0]:
            print("Error: Gas Card Not in Normal Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.N_labels, df))

    async def get_raw(self) -> dict:
        """Gets the raw sensor output.

        Returns:
            dict: Normal Channel (N1) mode Dataframe
        """
        if self._current_mode != "N1":
            await self.set_mode("N1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "N1" not in df[0]:
            print("Error: Gas Card Not in Normal Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.N1_labels, df))

    async def get_coeff(self) -> dict:
        """Gets the current value of the device.

        Returns:
            dict: Coefficient Channel (C1) mode dataframe
        """
        if self._current_mode != "C1":
            await self.set_mode("C1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "C" not in df[0]:
            print("Error: Gas Card Not in Coefficient Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.C1_labels, df))

    async def get_environmental(self) -> dict:
        """Gets environmental parameters.

        **WARNING Changing any environmental parameter will lead to incorrect gas sensor operation**

        Returns:
            dict: Environmental Mode (E1) dataframe
        """
        if self._current_mode != "E1":
            await self.set_mode("E1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "E" not in df[0]:
            print("Error: Gas Card Not in Environmental Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.E1_labels, df))

    async def get_output(self) -> dict:
        """Display and Change output variables.

        Returns:
            dict: Output Channel Mode (O1) dataframe
        """
        if self._current_mode != "O1":
            await self.set_mode("O1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "O" not in df[0]:
            print("Error: Gas Card Not in Output Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.O1_labels, df))

    async def get_settings(self) -> dict:
        """Display and Change Settings.

        Returns:
            dict: Settings mode (X) dataframe
        """
        if self._current_mode != "X":
            await self.set_mode("X")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "X" not in df[0]:
            print("Error: Gas Card Not in Settings Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.X_labels, df))

    async def get_userinterface(self) -> dict:
        """View user Interface.

        Returns:
            dict: User Interface mode (U) dataframe
        """
        if self._current_mode != "U":
            await self.set_mode("U")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "U" not in df[0]:
            print("Error: Gas Card Not in User Interface Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self.U_labels, df))

    async def get(self, vals: list) -> dict:
        """General function to receive from device.

        Args:
            vals (list): List of names (given in values dictionary) to receive from device.

        Returns:
            dict: Dictionary of names requested with their values
        """
        modes = []
        output = {}
        for val in vals:
            for key, value in self.values.items():
                for idx, names in enumerate(value[0]):
                    if val == names:  # I changed this from names to key
                        modes.append((key, names))
        unique_modes = {i[0] for i in modes}
        modes_func = {
            "N": self.get_val,
            "N1": self.get_raw,
            "C1": self.get_coeff,
            "E1": self.get_environmental,
            "O1": self.get_output,
            "X": self.get_settings,
            "U": self.get_userinterface,
        }
        for mode in unique_modes:
            ret = await modes_func[mode]()
            names = [i[1] for i in modes if i[0] == mode]
            output.update({names: ret[names] for names in names})
        return output

    async def set(self, params: dict) -> None:
        """General function to send to device.

        Args:
            params (dict): Variable:Value pairs for each desired set
        """
        modes = []
        for key, value in params.items():
            for key2, value2 in self.values.items():
                for idx, names in enumerate(value2[0]):
                    if key == names:
                        modes.append((key2, value2[1][idx], value))
        unique_modes = {i[0] for i in modes}
        # Go through each unique mode that a setting is changed in
        for mode in unique_modes:
            if self._current_mode != mode:
                # Change the mode to the correct one
                await self.set_mode(mode)
            # Send all the commands for that mode
            for val in [i for i in modes if i[0] == mode]:
                await self._device._write(f"{val[1]}{val[2]}")

        return

    async def zero(self) -> None:
        """Sets the zero reference of the device.

        **Device MUST be flowing zero gas BEFORE calling this function.**
        """
        await self.set({'Zero Gas Corr Factor':''})
        return

    async def span(self, val: float) -> None:
        """Sets the span reference of the device.

        **Device MUST be flowing span gas BEFORE calling this function.**

        Args:
            val (dict): Gas concentration as a fraction of full scale (0.5 to 1.2)
        """
        await self.set({'Span Gas Corr Factor':val})
        return
