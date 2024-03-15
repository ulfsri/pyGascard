from typing import Any, Union

import re
from abc import ABC

import trio
from comm import CommDevice, SerialDevice
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


async def new_device(port: str, id: str = "A", **kwargs: Any):
    """
    Creates a new device. Chooses appropriate device based on characteristics.
    """
    if port.startswith("/dev/"):
        device = SerialDevice(port, **kwargs)
    dev_info_raw = await device._write_readline("U")
    dev_info_raw = dev_info_raw.replace("\x00", "")
    dev_info = dict(zip(U_labels, dev_info_raw.split()))
    # If the sensor does not output a user interface mode line
    while not "U" in dev_info_raw.split()[0]:
        print("Error: Gas Card Not in User Interface Mode")
        dev_info_raw = await device._write_readline("U")
        dev_info_raw = dev_info_raw.replace("\x00", "")
        # Create a list of every word in the line
        dev_info = dev_info_raw.split()
    # dev_info = clean_mode(dev_info)
    return Gascard(device, dev_info, id, **kwargs)


class Gascard(ABC):
    """
    Gascard class.
    """

    def __init__(
        self, device: SerialDevice, dev_info: dict, id: str = "A", **kwargs: Any
    ) -> None:
        self._device = device
        self._id = id
        self._dev_info = dev_info
        self._df_format = None
        self._df_units = None

    async def get_val(self) -> dict:
        """
        Gets the current value of the device.
        """
        # If the format isn't established...
        if self._df_format != N_labels:
            # ...Create the format
            self._df_format = N_labels.copy()
        # Read the line
        ret = await self._device._write_readline("N")
        # Removes the hex indicators
        ret = ret.replace("\x00", "")
        # Create a list of every word in the line
        df = ret.split()
        # If the sensor does not output a normal mode line
        while not "N" in df[0]:
            print("Error: Gas Card Not in Normal Mode")
            # Repeat the above
            ret = await self._device._write_readline("N")
            ret = ret.replace("\x00", "")
            df = ret.split()
        # Convert numbers in the list into floats
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])
        # df = clean_mode(df)
        # Combine the format and the values into a dictionary
        return dict(zip(self._df_format, df))

    async def get_coeff(self) -> dict:
        """
        Gets the current value of the device.
        """
        # If the format isn't established...
        if self._df_format != C1_labels:
            # ...Create the format
            self._df_format = C1_labels.copy()
        # Read the line
        ret = await self._device._write_readline("C1")
        # Remove the hex indicators
        ret = ret.replace("\x00", "")
        # Create a list of every word in the line
        df = ret.split()
        # If the sensor does not output a coefficient mode line
        while not "C" in df[0]:
            print("Error: Gas Card Not in Coefficient Mode")
            # Repeat the above
            ret = await self._device._write_readline("C1")
            ret = ret.replace("\x00", "")
            df = ret.split()
        # Convert numbers in the list into floats
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])
        # Combine the format and the values into a dictionary
        return dict(zip(self._df_format, df))

    # There must be some way to let the user know which commands are vlid
    async def calibrate(self, com) -> None:
        """
        Allows user to start calibration routines or change coefficients
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
        """
        Display and Change Environmental Parameters
        com = The command code
        opt = to enable optional parts of the command
        WARNING Changing any environmental paramter will lead to incorrect gas sensor operation
        """
        # If the format isn't established...
        if self._df_format != E1_labels:
            # ...Create the format
            self._df_format = E1_labels.copy()
        # Read the line
        ret = await self._device._write_readline("E1")
        ret = ret.replace("\x00", "")
        # Create a list of every word in the line
        df = ret.split()
        # If the sensor does not output an environmental mode line
        while not "E" in df[0]:
            print("Error: Gas Card Not in Environmental Mode")
            # Repeat the above
            ret = await self._device._write_readline("E1")
            ret = ret.replace("\x00", "")
            df = ret.split()
        # Convert numbers in the list into floats
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])
        # Opt allows user to change parameters
        if opt.upper() == "Y":
            if com[0].upper() == "Z":  # Zero temp corr
                ret = await self._device._write_readline("z" + com[1:])
            elif com[0].upper() == "S":  # Span temp corr
                ret = await self._device._write_readline("s" + com[1:])
            elif com[0].upper() == "c":  # 4th order coeff
                ret = await self._device._write_readline("c" + com[1:])
            elif com[0].upper() == "D":  # 3rd order coeff
                ret = await self._device._write_readline("d" + com[1:])
            elif com[0].upper() == "E":  # 2nd order coeff
                ret = await self._device._write_readline("e" + com[1:])
            elif com[0].upper() == "G":  # 1st order coeff
                ret = await self._device._write_readline("g" + com[1:])
            elif com[0].upper() == "M":  # Slope corr
                ret = await self._device._write_readline("m" + com[1:])
            elif com[0].upper() == "X":  # Offset corr
                ret = await self._device._write_readline("x" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            # Read the line
            ret = await self._device._write_readline("E1")
            # Remove the hex indicators
            ret = ret.replace("\x00", "")
            # Create a list of every word in the line
            df = ret.split()
            # If the sensor does not output an environmental mode line
            while not "E" in df[0]:
                print("Error: Gas Card Not in Environmental Mode")
                # Repeat the above
                ret = await self._device._write_readline("E1")
                ret = ret.replace("\x00", "")
                df = ret.split()
            # Convert numbers in the list into floats
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index])
        # Combine the format and the values into a dictionary
        return dict(zip(self._df_format, df))

    async def output(self, com="", opt="n") -> str:
        """
        Display and Change Environmental Parameters
        """
        if self._df_format != O1_labels:  # If the format isn't established...
            self._df_format = O1_labels.copy()  # ...Create the format
        ret = await self._device._write_readline("O1")  # Read the line
        ret = ret.replace("\x00", "")
        df = ret.split()  # Create a list of every word in the line
        while not "O" in df[0]:  # If the sensor does not output an output mode line
            print("Error: Gas Card Not in Output Mode")
            ret = await self._device._write_readline("O1")  # Read the line again
            ret = ret.replace("\x00", "")  # Removes '\x00' characters
            df = ret.split()  # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])  # Convert numbers in the list into floats
        # opt = input("Would you like to change the output parameters? (y/n): ")
        if opt.upper() == "Y":
            # com = input(
            #     "Enter calibration command (m<val> = PWM volt output slope cal, x<val> = PWM volt output offset cal, a<val> = PWM current output slope cal, b<val> = PWM current output offset cal, v<val> = volt output range): "
            # )
            if com[0].upper() == "M":
                ret = await self._device._write_readline("m" + com[1:])
            elif com[0].upper() == "X":
                ret = await self._device._write_readline("x" + com[1:])
            elif com[0].upper() == "A":
                ret = await self._device._write_readline("a" + com[1:])
            elif com[0].upper() == "B":
                ret = await self._device._write_readline("b" + com[1:])
            elif com[0].upper() == "V":
                ret = await self._device._write_readline("v" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("O1")  # Read the line
            ret = ret.replace("\x00", "")
            df = ret.split()  # Create a list of every word in the line
            while not "O" in df[0]:  # If the sensor does not output an output mode line
                print("Error: Gas Card Not in output Mode")
                ret = await self._device._write_readline("E1")  # Read the line again
                ret = ret.replace("\x00", "")  # Removes '\x00' characters
                df = ret.split()  # Create a list of every word in the line
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(
                        df[index]
                    )  # Convert numbers in the list into floats
        return dict(
            zip(self._df_format, df)
        )  # Combine the format and the values into a dictionary

    async def settings(self, com="", opt="n") -> dict:
        """
        Display and Change Settings
        """
        # **SWITCHES STATE NOT IMPLEMENTED**
        # If the format isn't established...
        if self._df_format != X_labels:
            # ...Create the format
            self._df_format = X_labels.copy()
        # Read the line
        ret = await self._device._write_readline("X")
        # Remove the hex indicators
        ret = ret.replace("\x00", "")
        # Create a list of every word in the line
        df = ret.split()
        # If the sensor does not output a settings mode line
        while not "X" in df[0]:
            print("Error: Gas Card Not in Settings Mode")
            # Repeat the above
            ret = await self._device._write_readline("X")
            ret = ret.replace("\x00", "")
            df = ret.split()
        # Convert numbers in the list into floats
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])
        # opt lets user change settings
        if opt.upper() == "Y":
            if com[0].upper() == "F":  # Lamp freq
                opt = "y"  # WARNING: Changing the frequency will change the calibration coefficients.
                if opt.upper() == "Y":  # CLEAN THIS UP IAN, RELIC FROM INPUT
                    while float(com[1:]) < 1 or float(com[1:]) > 9:
                        print("Error: Frequency must be between 1 and 9")
                        return
                    if com[0].upper() != "F":
                        print("Invalid command")
                        return dict(zip(self._df_format, df))
                    await self._device._write_readline("s" + com[1:])
                    ret = await self._device._write_readline("f" + com[1:])
                else:
                    return dict(zip(self._df_format, df))
            elif com[0].upper() == "T":  # RC time const
                ret = await self._device._write_readline("t" + com[1:])
            elif com[0].upper() == "D":  # Reset all sensor variables
                opt = "y"  # WARNING: This will reset all sensor variables. This will render the sensor useless until re-setup.
                if opt.upper() == "Y":  # THIS ONE TOO
                    ret = await self._device._write_readline("d")
            elif com[0].upper() == "Q":  # Soft reset
                ret = await self._device._write_readline("q" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("X")
            ret = ret.replace("\x00", "")
            df = ret.split()
            while not "X" in df[0]:
                print("Error: Gas Card Not in settings Mode")
                ret = await self._device._write_readline("X")
                ret = ret.replace("\x00", "")
                df = ret.split()
            # Convert numbers in the list into floats
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index])
        # Combine the format and the values into a dictionary
        return dict(zip(self._df_format, df))

    async def userinterface(self, com="", opt="n") -> str:
        """
        View user Interface
        """
        if self._df_format != U_labels:
            self._df_format = U_labels.copy()  # ...Create the format
        ret = await self._device._write_readline("U")  # Read the line
        ret = ret.replace("\x00", "")
        df = ret.split()  # Create a list of every word in the line
        # If the sensor does not output a user interface mode line
        while not "U" in df[0]:
            print("Error: Gas Card Not in User Interface Mode")
            ret = await self._device._write_readline("U")
            ret = ret.replace("\x00", "")
            df = ret.split()
        # Convert numbers in the list into floats
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index])
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
            while not "X" in df[0]:
                print("Error: Gas Card Not in settings Mode")
                ret = await self._device._write_readline("X")
                ret = ret.replace("\x00", "")
                df = ret.split()
            # Convert numbers in the list into floats
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index])
        # Combine the format and the values into a dictionary
        return dict(zip(self._df_format, df))

    async def get_df_format(self) -> str:
        """
        Gets the format of the current dataframe format of the device
        """
        # Call the command to read the device (id + ??D*)
        resp = await self._device._write_readall(self._id + "??D*")
        splits = []
        # Breaks first line of output into iterable of match objects for each whitespace
        for match in re.finditer(r"\s", resp[0]):
            # Adds the start index/position of each match object to the list splits
            splits.append(match.start())
        df_table = [
            [k[i + 1 : j] for i, j in zip(splits, splits[1:] + [None])] for k in resp
        ]
        df_format = [
            i[[idx for idx, s in enumerate(df_table[0]) if "NAME" in s][0]].strip()
            for i in df_table[1:-1]
        ]
        df_ret = [
            i[[idx for idx, s in enumerate(df_table[0]) if "TYPE" in s][0]].strip()
            for i in df_table[1:-1]
        ]
        df_stand = [i for i in df_format if not (i.startswith("*"))]
        df_stand_ret = [i for i in df_ret[: len(df_stand)]]
        self._df_format = df_format
        self._df_ret = df_ret
        return [df_stand, df_stand_ret]

    async def get(self, comm: str) -> dict:
        """
        General function to receive from device.
        """
        if type(comm) != str:
            comm = str(comm)
        try:
            comm = commands[comm.lower()]
        except:
            print("Invalid command")
            return
        if comm[0].upper() == "N":
            return await self.get_val()
        elif comm[0].upper() == "C":
            return await self.get_coeff()
        elif comm[0].upper() == "E":
            return await self.environmental()
        elif comm[0].upper() == "O":
            return await self.output()
        elif comm[0].upper() == "X":
            return await self.settings()
        elif comm[0].upper() == "U":
            return await self.userinterface()
        return

    async def set(self, command: str, val=0) -> dict:
        """
        General function to send to device.
        """
        if type(command) != str:
            command = str(command)
        try:
            command = commands[command.lower()]
        except:
            print("Invalid command")
            return
        if command[0].upper() == "E":
            return await self.environmental(command[1:] + str(val), opt="y")
        elif command[0].upper() == "O":
            return await self.output(command[1:] + str(val), opt="y")
        elif command[0].upper() == "X":
            return await self.settings(command[1:] + str(val), opt="y")
        elif command[0].upper() == "U":
            return await self.userinterface(command[1:] + str(val), opt="y")
        return

    async def zero(self):
        """
        General function to zero the device.

        Device MUST be flowing zero gas BEFORE calling this function.
        """
        await self.calibrate("z")
        return

    async def span(self, val):
        """
        General function to span the device.

        Device MUST be flowing span gas BEFORE calling this function. Span value must be between 0.5 and 1.20
        """
        await self.calibrate("s" + val)
        return

    async def coefficients(self, hval, ival, jval, kval):
        """
        Set the calibration coefficients.
        """
        await self.calibrate("h" + hval)
        await self.calibrate("i" + ival)
        await self.calibrate("j" + jval)
        await self.calibrate("k" + kval)
        return
