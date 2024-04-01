from typing import Any

import re
from abc import ABC

from comm import SerialDevice
import trio
from trio import run

N_labels = [
    # Lists the outputs of the sensor in normal mode in order
    "Mode",
    "Conc 1",
    "Conc 2",
    "Conc 3",
    "Conc 4",
    "Conc 5",
    "Temperature",
    "Pressure",
    "Humidity",
]
N1_labels = [
    # Lists the outputs of the sensor in normal mode in order
    "Mode",
    "Sample Channel",
    "Reference Channel",
    "Voltage PWM Value",
    "Conc",
    "Sensor Temperature",
    "Sensor Pressure",
]
C1_labels = [
    # Lists the outputs of the sensor in coefficient mode in order
    "Mode",
    "CoeffA",
    "CoeffB",
    "CoeffC",
    "CoeffD",
    "Zero gas Corr. Factor",
    "Span gas Corr. Factor",
    "Zero Pot",
    "Span Pot",
    "Sam. Pot",
    "Ref. Pot",
]
E1_labels = [
    # Lists the outputs of the sensor in environmental mode in order
    "Mode",
    "Zero Cal. Temp.",
    "Span Cal. Temp.",
    "Pressure Sensor Slope Cor.",
    "Pressure Sensor Offset Cor.",
    "Press 4th Coeff",
    "Press 3rd Coeff",
    "Press 2nd Coeff",
    "Press 1st Coeff",
    "Zero Temp Correction Value",
    "Span Temp Correction Value",
]
O1_labels = [
    # Lists the outputs of the sensor in output mode in order
    "Mode",
    "PWM Voltage Output Slope Corr",
    "PWM Voltage Output Offset Corr",
    "PWM Voltage Value",
    "PWM Current Output Slope Corr",
    "PWM Current Output Offset Corr",
    "PWM Current Value",
]
X_labels = [
    # Lists the outputs of the sensor in settings mode in order
    "Mode",
    "Firmware Version",
    "Serial Number",
    "Config Register",
    "Frequency",
    "Time Constant",
    "Switches State",
]
U_labels = [
    # Lists the outputs of the sensor in user interface mode in order
    "Mode",
    "Gas Range",
    "Gas Type",
    "Background Gas",
    "Display selection",
]

commands = {
    "val": "N",
    "coeff": "C",
    "environmental": "E",
    "zero temp corr": "Ez",
    "span temp corr": "Es",
    "1st order coeff": "Eg",
    "2nd order coeff": "Ee",
    "3rd order coeff": "Ed",
    "4th order coeff": "Ec",
    "slope corr": "Em",
    "offset corr": "Ex",
    "output": "O",
    "pwm volt slope": "Om",
    "pwm volt offset": "Ox",
    "pwm current slope": "Oa",
    "pwm current offset": "Ob",
    "volt output range": "Ov",
    "settings": "X",
    "lamp freq": "Xf",
    "rc time const": "Xt",
    "reset all": "Xd",
    "soft reset": "Xq",
    "user interface": "U",
    "display selection": "Ud",
    "test leds": "Ut",
}

values = {  # Name of variable : [Mode, Command to change]
    "N": [N_labels, ["", "", "", "", "", "", "", "", ""]],
    "N1": [N1_labels, ["", "", "", "o", "", "", ""]],
    "C1": [C1_labels, ["", "h", "i", "j", "k", "z", "s", "", "", "p", "p"]],
    "E1": [E1_labels, ["", "", "", "m", "x", "c", "d", "e", "g", "z", "s"]],
    "O1": [O1_labels, ["", "m", "x", "", "a", "b", ""]],
    "X": [X_labels, ["", "", "", "", "f", "t", ""]],
    "U": [U_labels, ["", "", "", "", "d"]],
}


async def new_device(port: str, **kwargs: Any):
    """Creates a new device. Chooses appropriate device based on characteristics."""
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
        """Gets the current mode of the device."""
        ret = await self._device._readline()
        mode = ret[0:2].strip()
        if mode in self._modes:
            self.current_mode = mode
        else:
            print("Error: Invalid Mode")
        return mode

    async def set_mode(self, mode: str) -> None:
        """Sets the mode of the device."""
        if mode in self._modes:
            await self._device._write(mode)
            self._current_mode = mode
        else:
            print("Error: Invalid Mode")
        return

    async def get_val(self) -> dict:
        """Gets the current value of the device."""
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
        """Gets the raw sensor output."""
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
        """Gets the current value of the device."""
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

    # There must be some way to let the user know which commands are vlid

    async def calibrate(self, com) -> None:
        """Allows user to start calibration routines or change coefficients.

        Zero gas MUST be flowing before zeroing
        Span gas MUST be flowing before spanning
        Calibration commands: (z = zero, s<val> = span, h<val> = 1st coeff, i<val> = 2nd, j<val> = 3rd, k<val> = 4th)
        """
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
            await self._device._write_readline("s" + com[1:])
        elif com[0].upper() == "H":
            await self._device._write_readline("h" + com[1:])
        elif com[0].upper() == "I":
            await self._device._write_readline("i" + com[1:])
        elif com[0].upper() == "J":
            await self._device._write_readline("j" + com[1:])
        elif com[0].upper() == "K":
            await self._device._write_readline("k" + com[1:])
        else:
            print("Invalid command")  # Note the p command hasn't be included
            self.calibrate()
        return

    async def environmental(self, com="", opt="n") -> str:
        """Display and Change Environmental Parameters.

        com = The command code
        opt = to enable optional parts of the command
        WARNING Changing any environmental parameter will lead to incorrect gas sensor operation
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
        if opt.upper() == "Y":
            valid_commands = ["Z", "S", "C", "D", "E", "G", "M", "X"]
            if com[0].upper() in valid_commands:
                ret = await self._device._write_readline(com[0].lower + com[1:])
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

    async def output(self, com="", opt="n") -> str:
        """Display and Change output variables."""
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
                ret = await self._device._write_readline(com[0].lower() + com[1:])
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

    async def settings(self, com="", opt="n") -> dict:
        """Display and Change Settings."""
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
                    await self._device._write_readline(
                        command_mapping[command] + com[1:]
                    )
                    ret = await self._device._write_readline("f" + com[1:])
                else:
                    ret = await self._device._write_readline(
                        command_mapping[command] + com[1:]
                    )
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

    async def userinterface(self, com="", opt="n") -> str:
        """View user Interface."""
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
                ret = await self._device._write_readline("d" + com[1:])
            elif com[0].upper() == "T":  # Test LEDs and display
                ret = await self._device._write_readline("t" + com[1:])
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

        vals is list of names (given in values dictionary) to receive from device.
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
        """General function to send to device."""
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

    async def zero(self):
        """General function to zero the device.

        Device MUST be flowing zero gas BEFORE calling this function.
        """
        await self.calibrate("z")
        return

    async def span(self, val):
        """General function to span the device.

        Device MUST be flowing span gas BEFORE calling this function. Span value must be between 0.5 and 1.20
        """
        await self.calibrate("s" + val)
        return

    async def coefficients(self, hval, ival, jval, kval):
        """Set the calibration coefficients."""
        await self.calibrate("h" + hval)
        await self.calibrate("i" + ival)
        await self.calibrate("j" + jval)
        await self.calibrate("k" + kval)
        return
