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
    "Current Temperature",
    "Current Pressure",
    "Current Humidity",
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
    "Pressure Sensor Slope Cor. (m)",
    "Pressure Sensor Offset Cor. (x)",
    "Press 4th Coeff (c)",
    "Press 3rd Coeff (d)",
    "Press 2nd Coeff (e)",
    "Press 1st Coeff (g)",
    "Zero Temp Correction Value (z)",
    "Span Temp Correction Value (s)",
]
O1_labels = [
    # Lists the outputs of the sensor in output mode in order
    "Mode",
    "PWM Voltage Output Slope Corr (m)",
    "PWM Voltage Output Offset Corr (c)",
    "PWM Voltage Value",
    "PWM Current Output Slope Corr (a)",
    "PWM Current Output Offset Corr (b)",
    "PWM Current Value",
]
X_labels = [
    # Lists the outputs of the sensor in settings mode in order
    "Mode",
    "Firmware Version",
    "Serial Number",
    "Config Register",
    "Frequency (f)",
    "Time Constant (t)",
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

# This function is not necessary, but would've resulted in more visual appealling responses
'''
def clean_mode(word_list) -> list:
    """
    Function removes duplicate characters in 'mode' item
    Returns:
        list: parameter with duplicates removed from 1st item
    """
    cleaned_list = word_list.copy()
    print(cleaned_list[0])
    if len(cleaned_list[0]) > 1:
        for i in range(len(cleaned_list[0])):
             if cleaned_list[0].count(cleaned_list[0][i]) > 1:
                 cleaned_list[0].replace(cleaned_list[0][i], " ")
    cleaned_list[0] = cleaned_list[0].replace(" ","")
    return str(cleaned_list)
'''


async def new_device(port: str, **kwargs: Any):
    """Creates a new device. Chooses appropriate device based on characteristics."""
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info_raw = await device._write_readline("U")
    dev_info_raw = dev_info_raw.replace("\x00", "")
    dev_info = dict(zip(U_labels, dev_info_raw.split()))
    # If the sensor does not output a user interface mode line
    while "U" not in dev_info_raw.split()[0]:
        print("Error: Gas Card Not in User Interface Mode")
        dev_info_raw = await device._write_readline("U")
        dev_info_raw = dev_info_raw.replace("\x00", "")
        # Create a list of every word in the line
        dev_info = dev_info_raw.split()
    # dev_info = clean_mode(dev_info)
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

    async def get_val(self) -> dict:
        """Gets the current value of the device."""
        if self._df_format != N_labels:
            self._df_format = N_labels.copy()
        ret = await self._device._write_readline("N")
        ret = ret.replace("\x00", "")
        df = ret.split()
        while "N" not in df[0]:
            print("Error: Gas Card Not in Normal Mode")
            ret = await self._device._write_readline("N")
            ret = ret.replace("\x00", "")
            df = ret.split()
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self._df_format, df))

    async def get_coeff(self) -> dict:
        """Gets the current value of the device."""
        if self._df_format != C1_labels:
            self._df_format = C1_labels.copy()
        ret = await self._device._write_readline("C1")
        ret = ret.replace("\x00", "")
        df = ret.split()
        while "C" not in df[0]:
            print("Error: Gas Card Not in Coefficient Mode")
            ret = await self._device._write_readline("C1")
            ret = ret.replace("\x00", "")
            df = ret.split()
        for index in range(len(df)):
            try:
                df[index] = float(df[index])
            except ValueError:
                pass
        return dict(zip(self._df_format, df))

    # There must be some way to let the user know which commands are vlid

    async def calibrate(self, com) -> None:
        """Allows user to start calibration routines or change coefficients.

        Zero gas MUST be flowing before zeroing
        Span gas MUST be flowing before spanning
        Calibration commands: (z = zero, s<val> = span, h<val> = 1st coeff, i<val> = 2nd, j<val> = 3rd, k<val> = 4th).
        """
        valid_commands = ["Z", "S", "H", "I", "J", "K"]
        if com.upper() in valid_commands:
            if com.upper() == "S":
                span_value = com[1:]
                if float(span_value) < 0.5 or float(span_value) > 1.20:
                    print("Error: Span value must be between 0.5 and 1.20")
                    return
                await self._device._write_readline(com + span_value)
            else:
                await self._device._write_readline(com + com[1:])
        else:
            print("Invalid command")
        return

    async def environmental(self, com="", opt="n") -> str:
        """Display and Change Environmental Parameters.

        com = The command code
        opt = to enable optional parts of the command
        WARNING Changing any environmental parameter will lead to incorrect gas sensor operation
        """
        if self._df_format != E1_labels:
            self._df_format = E1_labels.copy()
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
        if opt.upper() == "Y":
            valid_commands = ["Z", "S", "C", "D", "E", "G", "M", "X"]
            if com.upper() in valid_commands:
                ret = await self._device._write_readline(com + com[1:])
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
        return dict(zip(self._df_format, df))

    async def output(self, com="", opt="n") -> str:
        """Display and Change Environmental Parameters."""
        if self._df_format != O1_labels:
            self._df_format = O1_labels.copy()
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
        if opt.upper() == "Y":
            valid_commands = ["M", "X", "A", "B", "V"]
            if com.upper() in valid_commands:
                ret = await self._device._write_readline(com + com[1:])
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
        return dict(zip(self._df_format, df))

    async def settings(self, com="", opt="n") -> dict:
        """Display and Change Settings."""
        if self._df_format != X_labels:
            self._df_format = X_labels.copy()
        ret = await self._device._write_readline("X")
        ret = ret.replace("\x00", "")
        df = ret.split()
        while "X" not in df[0]:
            print("Error: Gas Card Not in Settings Mode")
            ret = await self._device._write_readline("X")
            ret = ret.replace("\x00", "")
            df = ret.split()
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])
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
        return dict(zip(self._df_format, df))

    async def userinterface(self, com="", opt="n") -> str:
        """View user Interface."""
        if self._df_format != U_labels:
            self._df_format = U_labels.copy()  # Create the format
        ret = await self._device._write_readline("U")  # Read the line
        ret = ret.replace("\x00", "")
        df = ret.split()  # Create a list of every word in the line
        # If the sensor does not output a user interface mode line
        while "U" not in df[0]:
            print("Error: Gas Card Not in User Interface Mode")
            ret = await self._device._write_readline("U")
            ret = ret.replace("\x00", "")
            df = ret.split()
        # Convert numbers in the list into floats
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
        return dict(zip(self._df_format, df))

    async def get(self, comm: str) -> dict:
        """General function to receive from device."""
        if not isinstance(comm, str):
            comm = str(comm)
        try:
            comm = commands[comm.lower()]
        except KeyError:
            print("Invalid command")
            return
        command_mapping = {
            "N": self.get_val,
            "C": self.get_coeff,
            "E": self.environmental,
            "O": self.output,
            "X": self.settings,
            "U": self.userinterface,
        }
        if comm[0].upper() in command_mapping:
            return await command_mapping[comm[0].upper()]()
        return

    async def set(self, command: str, val=0) -> dict:
        """General function to send to device."""
        if not isinstance(command, str):
            command = str(command)
        try:
            command = commands[command.lower()]
        except KeyError:
            print("Invalid command")
            return
        command_mapping = {
            "E": self.environmental,
            "O": self.output,
            "X": self.settings,
            "U": self.userinterface,
        }
        if command[0].upper() in command_mapping:
            return await command_mapping[command[0].upper()](
                command[1:] + str(val), opt="y"
            )

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
