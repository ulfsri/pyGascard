"""Gascard device class.

Raises:
    ValueError: If device is not in the correct mode.
    ValueError: If device is not found on port.
    ValueError: If mode is invalid.
    ValueError: If gas is not accepted.

Returns:
    _type_: _description_
"""

import importlib
import json
from abc import ABC
from typing import Any

from pygascard.comm import SerialDevice

codes = importlib.resources.files("pygascard").joinpath("codes.json")
with open(codes) as f:
    codes = json.load(f)
values = codes["values"]
N_labels = values["N"][0]
N1_labels = values["N1"][0]
C1_labels = values["C1"][0]
E1_labels = values["E1"][0]
O1_labels = values["O1"][0]
X_labels = values["X"][0]
U_labels = values["U"][0]


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
        self._MODES = (
            "N",
            "N1",
            "C1",
            "E1",
            "O1",
            "D",
            "X",
            "U",
        )

    @classmethod
    async def new_device(cls, port: str, **kwargs: Any) -> "Gascard":
        """Creates a new device. Chooses appropriate device based on characteristics.

        Example:
            dev = run(Gascard.new_device, "/dev/ttyUSB4")

        Args:
            port (str): The port of the device.
            **kwargs: Any

        Returns:
            Device: The new device.
        """
        if port.startswith("/dev/"):
            device = SerialDevice(port, **kwargs)
        await device._write("U")
        dev_info_raw = await device._readline()
        if not dev_info_raw:
            raise ValueError("No device found on port")
        dev_info_raw = dev_info_raw.replace("\x00", "")
        dev_info = dict(zip(U_labels, dev_info_raw.split()))
        if "U" not in dev_info_raw.split()[0]:
            # print("Error: Gas Card Not in User Interface Mode")
            raise ValueError("Gas Card Not in User Interface Mode")
        return cls(device, dev_info, **kwargs)

    async def _get_mode(self) -> str:
        """Gets the current mode of the device.

        Returns:
            str: Current mode of device
        """
        ret = await self._device._readline()
        mode = ret[:2].strip()
        if mode in self._MODES:
            self.current_mode = mode
        else:
            # print("Error: Invalid Mode")
            raise ValueError("Invalid Mode")
        return mode

    async def _set_mode(self, mode: str) -> None:
        """Sets the mode of the device.

        Args:
            mode (str): Desired mode for device
        """
        if mode in self._MODES:
            await self._device._write(mode)
            self._current_mode = mode
        else:
            # print("Error: Invalid Mode")
            raise ValueError("Invalid Mode")
        return

    async def _get_val(self) -> dict[str, str | float]:
        """Gets the current value of the device.

        Returns:
            dict[str, str | float]: Normal (N) mode dataframe
        """
        if self._current_mode != "N":
            await self._set_mode("N")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "N" not in df[0]:
            # print("Error: Gas Card Not in Normal Mode")
            raise ValueError("Gas Card Not in Normal Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(N_labels, df))

    async def _get_raw(self) -> dict[str, str | float]:
        """Gets the raw sensor output.

        Returns:
            dict[str, str | float]: Normal Channel (N1) mode Dataframe
        """
        if self._current_mode != "N1":
            await self._set_mode("N1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "N1" not in df[:2]:
            # print("Error: Gas Card Not in Normal Mode")
            raise ValueError("Gas Card Not in Normal Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(N1_labels, df))

    async def _get_coeff(self) -> dict[str, str | float]:
        """Gets the current value of the device.

        Returns:
            dict[str, str | float]: Coefficient Channel (C1) mode dataframe
        """
        if self._current_mode != "C1":
            await self._set_mode("C1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "C1" not in df[:2]:
            # print("Error: Gas Card Not in Coefficient Mode")
            raise ValueError("Gas Card Not in Coefficient Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(C1_labels, df))

    async def _get_environmental(self) -> dict:
        """Gets environmental parameters.

        Note:
            **WARNING Changing any environmental parameter will lead to incorrect gas sensor operation**

        Returns:
            dict: Environmental Mode (E1) dataframe
        """
        if self._current_mode != "E1":
            await self._set_mode("E1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "E" not in df[0]:
            # print("Error: Gas Card Not in Environmental Mode")
            raise ValueError("Gas Card Not in Environmental Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(E1_labels, df))

    async def _get_output(self) -> dict[str, str | float]:
        """Display and Change output variables.

        Returns:
            dict[str, str | float]: Output Channel Mode (O1) dataframe
        """
        if self._current_mode != "O1":
            await self._set_mode("O1")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "O1" not in df[0:2]:
            # print("Error: Gas Card Not in Output Mode")
            raise ValueError("Gas Card Not in Output Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(O1_labels, df))

    async def _get_settings(self) -> dict[str, str | float]:
        """Display and Change Settings.

        Returns:
            dict[str, str | float]: Settings mode (X) dataframe
        """
        if self._current_mode != "X":
            await self._set_mode("X")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "X" not in df[0]:
            # print("Error: Gas Card Not in Settings Mode")
            raise ValueError("Gas Card Not in Settings Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(X_labels, df))

    async def _get_userinterface(self) -> dict[str, str | float]:
        """View user Interface.

        Returns:
            dict[str, str | float]: User Interface mode (U) dataframe
        """
        acc_gas = ["CO", "CO2", "CH4"]
        if self._current_mode != "U":
            await self._set_mode("U")
        ret = await self._device._readline()
        ret = ret.replace("\x00", "")
        df = ret.split()
        if "U" not in df[0]:
            # print("Error: Gas Card Not in User Interface Mode")
            raise ValueError("Gas Card Not in User Interface Mode")
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        if df[2] not in acc_gas:
            # print("Error: Gas Not Accepted")
            raise ValueError("Gas Not Accepted")
        return dict(zip(U_labels, df))

    async def get(self, vals: list[str] = "") -> dict[str, str | float]:
        """General function to receive from device.

        Max acquisition rate seems to be 4 Hz

        Example:
            df = run(dev.get, ["Gas Type", "Gas Range", "Conc 1"])
            df = run(dev.get, "Gas Type")

        Args:
            vals (list[str]): List of names (given in values dictionary) to receive from device.

        Returns:
            dict[str, str | float]: Dictionary of names requested with their values
        """
        if not vals:
            return await self._get_val()
        if not isinstance(vals, list):
            vals = vals.split()
        modes = []
        output = {}
        for val in vals:
            for key, value in values.items():
                for idx, names in enumerate(value[0]):
                    if val == names:
                        modes.append((key, names))
        unique_modes = {i[0] for i in modes}
        MODES_FUNC = {
            "N": self._get_val,
            "N1": self._get_raw,
            "C1": self._get_coeff,
            "E1": self._get_environmental,
            "O1": self._get_output,
            "X": self._get_settings,
            "U": self._get_userinterface,
        }
        for mode in unique_modes:
            ret = await MODES_FUNC[mode]()
            names = [i[1] for i in modes if i[0] == mode]
            output.update({names: ret[names] for names in names})
        return output

    async def set(self, params: dict[str, str | float]) -> None:
        """General function to send to device.

        Example:
            df = run(dev.set, {"Time Constant": 0, "Pressure Sensor Offset Cor": 904})

        Args:
            params (dict[str, str | float]): Variable:Value pairs for each desired set
        """
        modes = []
        for key, value in params.items():
            for key2, value2 in values.items():
                for idx, names in enumerate(value2[0]):
                    if key == names:
                        modes.append((key2, value2[1][idx], value))
        unique_modes = {i[0] for i in modes}
        for mode in unique_modes:
            if self._current_mode != mode:
                await self._set_mode(mode)
            for val in [i for i in modes if i[0] == mode]:
                await self._device._write(f"{val[1]}{val[2]}")
        return

    async def zero(self) -> None:
        """Sets the zero reference of the device.

        Example:
            df = run(dev.zero)

        Note:
            **Device MUST be flowing zero gas BEFORE calling this function.**
        """
        await self.set({"Zero Gas Corr Factor": ""})
        return

    async def span(self, val: float) -> None:
        """Sets the span reference of the device.

        Example:
            df = run(dev.span, 0.2126)

        Note:
            **Device MUST be flowing span gas BEFORE calling this function.**

        Args:
            val (dict[str, float]): Gas concentration as a fraction of full scale (0.5 to 1.2)
        """
        await self.set({"Span Gas Corr Factor": val})
        return

    async def time_const(self, val: int) -> None:
        """Sets the time constant of the RC filter of the device.

        Example:
            df = run(dev.time_const, 0)

        Args:
            val (int): Time constant in seconds (0 to 120)
        """
        await self.set({"Time Constant": val})
        return
