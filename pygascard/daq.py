"""DAQ Class for managing gascard devices. Accessible to external API and internal logging module.

Author: Grayson Bellamy
Date: 2024-01-07
"""

from typing import Any
import device
from trio import run


class DAQ:
    """Class for managing gascard devices. Accessible to external API and internal logging module. Wraps and allows communication with inidividual or all devices through wrapper class."""

    def __init__(self) -> None:
        """Initializes the DAQ.

        TODO: Pass dictionary of names and addresses to initialize devices. Same async issue.

        """
        global dev_list
        dev_list = {}

        """
        for name in devs:
            dev = device.new_device(devs[name])
            dev_list.update({name: dev})
        """
        return

    @classmethod
    async def init(cls, devs: dict[str, str | device.Gascard]) -> "DAQ":
        """Initializes the DAQ.

        Example:
            Daq = run(DAQ.init, {'A':'/dev/ttyUSB4', 'B':'/dev/ttyUSB5'})

        Args:
            devs (dict[str, str | device.Gascard]): The dictionary of devices to add. Name:Port

        Returns:
            DAQ: The DAQ object.
        """
        daq = cls()
        await daq.add_device(devs)
        return daq

    async def add_device(
        self, devs: dict[str, str | device.Gascard], **kwargs: Any
    ) -> None:
        """Creates and initializes the devices.

        Args:
            devs (dict[str, str | device.Gascard]): The dictionary of devices to add. Name:Port
            **kwargs: Any
        """
        if devs:
            if isinstance(devs, str):
                devs = devs.split()
                # This works if the string is the format "Name Port"
                devs = {devs[0]: devs[1]}
            for name in devs:
                if isinstance(devs[name], str):
                    dev = await device.Gascard.new_device(devs[name])
                    dev_list.update({name: dev})
                elif isinstance(devs[name], device.Gascard):
                    dev_list.update({name: devs[name]})
        return

    async def remove_device(self, name: list[str]) -> None:
        """Removes the devices.

        Args:
            name (list[str]): The list of names of devices to remove.
        """
        for n in name:
            await dev_list[n]._device.close()
            del dev_list[n]
        return

    async def dev_list(self) -> dict[str, device.Gascard]:
        """Displays the list of devices.

        Returns:
            dict[str, device.Gascard]: The list of devices and their objects.
        """
        return dev_list

    async def get(
        self, val: list[str] = "", id: list[str] = ""
    ) -> dict[str, str | float]:
        """Gets the data from the device.

        If id not specified, returns data from all devices.

        Example:
            df = run(Daq.get, ["Gas Type", "Gas Range", "Conc 1"], ['A', 'B'])
            df = run(Daq.get, ["Gas Type", "Gas Range", "Conc 1"])
            df = run(Daq.get, ["Gas Type", "Gas Range", "Conc 1"], 'B')
            df = run(Daq.get, "Gas Type")

        Args:
           val (list[str]): The values to get from the device.
           id (list[str]): The IDs of the devices to read from. If not specified, returns data from all devices.

        Returns:
            dict[str, str | float]: The dictionary of devices with the data for each value.
        """
        ret_dict = {}
        if isinstance(val, str):
            val = [val]
        if not id:
            for dev in dev_list:
                ret_dict.update({dev: await dev_list[dev].get(val)})
        if isinstance(id, str):
            id = id.split()
        for i in id:
            ret_dict.update({i: await dev_list[i].get(val)})
        return ret_dict

    async def set(
        self, command: dict[str, str | float], id: list[str] = ""
    ) -> dict[str, None]:
        """Sets the data of the device.

        Example:
            df = run(Daq.set, {"Time Constant": 0, "Pressure Sensor Offset Cor": 904})
            df = run(Daq.set, {"Time Constant": 0, "Pressure Sensor Offset Cor": 904}, ['A', 'B'])
            df = run(Daq.set, {"Pressure Sensor Offset Cor": 933}, ["B"])

        Args:
           command (dict[str, str | float]): The commands and their relevant parameters to send to the device.
           id (list[str]): The IDs of the devices to read from. If not specified, returns data from all devices.

        Returns:
            dict[str, None]: The dictionary of devices changed.
        """
        ret_dict = {}
        if isinstance(command, str):
            command = command.split()
        if not id:
            for dev in dev_list:
                ret_dict.update({dev: await dev_list[dev].set(command)})
        if isinstance(id, str):
            id = id.split()
        for i in id:
            ret_dict.update({i: await dev_list[i].set(command)})
        return ret_dict

    async def zero(self, id: list[str] = "") -> None:
        """Sets the zero reference of the device.

        Note:
            **Device MUST be flowing zero gas BEFORE calling this function.**

        Example:
            df = run(Daq.zero, ['A', 'B'])
            df = run(Daq.zero, 'B')
            df = run(Daq.zero)

        Args:
            id (list[str]): The IDs of the devices to read from. If not specified, returns data from all devices.
        """
        ret_dict = {}
        if not id:
            for dev in dev_list:
                ret_dict.update(
                    {dev: await dev_list[i].set({"Zero Gas Corr Factor": ""})}
                )
        if isinstance(id, str):
            id = id.split()
        for i in id:
            ret_dict.update({i: await dev_list[i].set({"Zero Gas Corr Factor": ""})})
        return ret_dict

    async def span(self, val: float, id: list[str] = "") -> None:
        """Sets the span reference of the device.

        Note:
            **Device MUST be flowing span gas BEFORE calling this function.**

        Example:
            df = run(Daq.span, 0.2126, ['A', 'B'])
            df = run(Daq.span, 0.2677, 'B')
            df = run(Daq.span)

        Args:
            val (float): Gas concentration as a fraction of full scale (0.5 to 1.2)
            id (list[str]): The IDs of the devices to read from. If not specified, returns data from all devices.
        """
        ret_dict = {}
        if not id:
            for dev in dev_list:
                ret_dict.update(
                    {dev: await dev_list[i].set({"Span Gas Corr Factor": val})}
                )
        if isinstance(id, str):
            id = id.split()
        for i in id:
            ret_dict.update({i: await dev_list[i].set({"Span Gas Corr Factor": val})})
        return ret_dict

    async def time_const(self, val: int, id: list[str] = "") -> None:
        """Sets the time constant of the RC filter of the device.

        Example:
            df = run(Daq.time_const, 0, ['A', 'B'])

        Args:
            val (int): Time constant in seconds (0 to 120)
            id (list[str]): The IDs of the devices to read from. If not specified, returns data from all devices.
        """
        ret_dict = {}
        if not id:
            for dev in dev_list:
                await dev_list[dev].set({"Time Constant": val})
        if isinstance(id, str):
            id = id.split()
        for i in id:
            await dev_list[i].set({"Time Constant": val})
        return


class DAQLogging:
    """Class for logging the data from gascard devices. Creates and saves file to disk with given acquisition rate. Only used for standalone logging. Use external API for use as plugin."""

    def __init__(self, config: dict) -> None:
        """Initializes the Logging module. Creates and saves file to disk with given acquisition rate.

        Parameters
        ----------
        config : dict
            The configuration dictionary. {Name : port}
        """
        pass
