from typing import Any

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
commands = codes["commands"][0]
values = codes["values"][0]

async def new_device(port: str, **kwargs: Any):
    """Creates a new device. Chooses appropriate device based on characteristics.

    Args:
        **kwargs: Any

    Returns:
        Device: The new device.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info_raw = await device._write_readline("U")
    dev_info_raw = dev_info_raw.replace("\x00", "")
    dev_info = dict(zip(U_labels, dev_info_raw.split()))
    # If the sensor does not output a user interface mode line
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
        self._df_format = None
        self._current_mode = "U"
        self._modes = [
            "N",
            "N1",
            "C",
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

    # There must be some way to let the user know which commands are valid

    async def calibrate(self, com: str) -> None:
        """Allows user to start calibration routines or change coefficients.

        Zero gas MUST be flowing before zeroing
        Span gas MUST be flowing before spanning
        Calibration commands: (z = zero, s<val> = span, h<val> = 1st coeff, i<val> = 2nd, j<val> = 3rd, k<val> = 4th)
        
        
        Args:
            com (str): The command for the device
        """
        # await self._device._write_readline(f"{com[0].lower()}{com[1:]}")
        # Zero gas
        if com.upper() == "Z":
            await self._device._write_readline("z")
        # Span gas
        elif com[0].upper() == "S":
            while float(com[1:]) < 0.5 or float(com[1:]) > 1.20:
                print("Error: Span value must be between 0.5 and 1.20")
                return
            if com[0].upper() != "S":
                print("Invalid command")
                return
            # input("Press enter once span gas is flowing")
            await self._device._write_readline(f"s{com[1:]}")
        elif com[0].upper() == "H":
            await self._device._write_readline(f"h{com[1:]}")
        elif com[0].upper() == "I":
            await self._device._write_readline(f"i{com[1:]}")
        elif com[0].upper() == "J":
            await self._device._write_readline(f"j{com[1:]}")
        elif com[0].upper() == "K":
            await self._device._write_readline(f"k{com[1:]}")
        else:
            print("Invalid command")  # Note the p command hasn't be included
            self.calibrate()
        return

    async def environmental(self, com: str = "", opt: bool = False) -> dict:
        """Display and Change Environmental Parameters.

        WARNING Changing any environmental parameter will lead to incorrect gas sensor operation
        
        Args:
            com (str): The command for the device
            opt (bool): To enable optional parts of the command
        
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
        if opt:
            valid_commands = ["Z", "S", "C", "D", "E", "G", "M", "X"]
            if com[0].upper() in valid_commands:
                ret = await self._device._write_readline(f"{com[0].lower}{com[1:]}")
                ret = await self._device._write_readline("E1")
                ret = ret.replace("\x00", "")
                df = ret.split()
                while "E" not in df[0]:
                    print("Error: Gas Card Not in Environmental Mode")
                    ret = await self._device._write_readline("E1")
                    ret = ret.replace("\x00", "")
                    df = ret.split()
                for index in range(len(df)):
                    try:
                        df[index] = float(df[index])
                    except ValueError:
                        pass
            else:
                print("Invalid command")
        return dict(zip(self.E1_labels, df))

    async def output(self, com: str = "", opt: bool = False) -> dict:
        """Display and Change output variables.
        
        Args:
            com (str): The command for the device
            opt (bool): To enable optional parts of the command
        
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
        if opt.upper() == "Y":
            valid_commands = ["M", "X", "A", "B", "V"]
            if com[0].upper() in valid_commands:
                ret = await self._device._write_readline(f"{com[0].lower()}{com[1:]}")
                ret = await self._device._write_readline("O1")
                ret = ret.replace("\x00", "")
                df = ret.split()
                while "O" not in df[0]:
                    print("Error: Gas Card Not in Output Mode")
                    ret = await self._device._write_readline("O1")
                    ret = ret.replace("\x00", "")
                    df = ret.split()
                for index in range(len(df)):
                    try:
                        df[index] = float(df[index])
                    except ValueError:
                        pass
            else:
                print("Invalid command")
        return dict(zip(self.O1_labels, df))

    async def settings(self, com: str = "", opt: bool = False) -> dict:
        """Display and Change Settings.
        
        Args:
            com (str): The command for the device
            opt (bool): To enable optional parts of the command
        
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
        if opt.upper() == "Y":
            command_mapping = {
                "F": "s",
                "T": "t",
                "D": "d",
                "Q": "q",
            }
            command = com.upper()
            if command in command_mapping:
                if command == "F":
                    if float(com[1:]) < 1 or float(com[1:]) > 9:
                        print("Error: Frequency must be between 1 and 9")
                        return dict(zip(self._df_format, df))
                    await self._device._write_readline(f"{command_mapping[command]}{com[1:]}")
                    ret = await self._device._write_readline(f"f{com[1:]}")
                else:
                    ret = await self._device._write_readline(f"{command_mapping[command]}{com[1:]}")
            else:
                print("Invalid command")
            ret = await self._device._write_readline("X")
            ret = ret.replace("\x00", "")
            df = ret.split()
            while "X" not in df[0]:
                print("Error: Gas Card Not in settings Mode")
                ret = await self._device._write_readline("X")
                ret = ret.replace("\x00", "")
                df = ret.split()
            for index in range(len(df)):
                try:
                    df[index] = float(df[index])
                except ValueError:
                    pass
        return dict(zip(self.X_labels, df))

    async def userinterface(self, com: str = "", opt: bool = False) -> dict:
        """View user Interface.
        
        Args:
            com (str): The command for the device
            opt (bool): To enable optional parts of the command
        
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
        # opt lets user to display or test
        if opt.upper() == "Y":
            if com[0].upper() == "D":  # Display selection
                ret = await self._device._write_readline(f"d{com[1:]}")
            elif com[0].upper() == "T":  # Test LEDs and display
                ret = await self._device._write_readline(f"t{com[1:]}")
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("X")  # Read the line
            ret = ret.replace("\x00", "")
            df = ret.split()  # Create a list of every word in the line
            # If the sensor does not output an settings mode line
            while "X" not in df[0]:
                print("Error: Gas Card Not in settings Mode")
                ret = await self._device._write_readline("X")
                ret = ret.replace("\x00", "")
                df = ret.split()
            # Convert numbers in the list into floats
            for index in range(len(df)):
                try:
                    df[index] = float(df[index])
                except ValueError:
                    pass
        # Combine the format and the values into a dictionary
        return dict(zip(self.U_labels, df))

    async def get(self, vals: list) -> dict:
        """General function to receive from device.
        
        Args:
            vals (list): List of names (given in values dictionary) to receive from device.
        
        Returns:
            dict: Combined dataframe with function calls
        """
        modes = []
        output = {}
        for val in vals:
            for key, value in self.values.items():
                for idx, names in enumerate(value[0]):
                    if val == names:
                        modes.append((key, names))
        unique_modes = {i[0] for i in modes}
        modes_func = {
            "N": self.get_val,
            "N1": self.get_raw,
            "C1": self.get_coeff,
            "E1": self.environmental,
            "O1": self.output,
            "X": self.settings,
            "U": self.userinterface,
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
        """General function to zero the device.

        Device MUST be flowing zero gas BEFORE calling this function.
        """
        await self.calibrate("z")
        return

    async def span(self, val: float) -> None:
        """General function to span the device.

        Device MUST be flowing span gas BEFORE calling this function.
        
        Args:
            val (dict): Gas concentration as a fraction of full scale (0.5 to 1.2)
        """
        await self.calibrate(f"s{val}")
        return

    async def coefficients(self, hval: float, ival: float, jval: float, kval: float) -> None:
        """Set the calibration coefficients.
        
        Args:
            hval (float): 1st Order Linearization coeff
            ival (float): 2nd Order Linearization coeff
            jval (float): 3rd Order Linearization coeff
            kval (float): 4th Order Linearization coeff
        """
        await self.calibrate(f"h{hval}")
        await self.calibrate(f"i{ival}")
        await self.calibrate(f"j{jval}")
        await self.calibrate(f"k{kval}")
        return
