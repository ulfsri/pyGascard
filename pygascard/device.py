import trio
from trio import run
from comm import CommDevice, SerialDevice
from typing import Any, Union
from abc import ABC
import re


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
    "Current Humidity"
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
    "Ref. Pot"
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
    "PWM Current Value"
]
X_labels = [
    # Lists the outputs of the sensor in settings mode in order
    "Mode",
    "Firmware Version",
    "Serial Number",
    "Config Register",
    "Frequency (f)",
    "Time Constant (t)",
    "Switches State"
]
U_labels = [
    # Lists the outputs of the sensor in user interface mode in order
    "Mode",
    "Gas Range",
    "Gas Type",
    "Background Gas",
    "Display selection"
]

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
    dev_info = dict(
        zip(U_labels, dev_info_raw.split())
    )
    while not 'U' in dev_info_raw.split()[0]: # If the sensor does not output a user interface mode line
            print("Error: Gas Card Not in User Interface Mode")
            dev_info_raw = await device._write_readline("U")
            dev_info_raw = dev_info_raw.replace("\x00", "")
            dev_info = dev_info_raw.split() # Create a list of every word in the line
    print(dev_info)
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

    async def get(self) -> str:
        """
        Gets the current value of the device.
        """ 
        if self._df_format != N_labels: # If the format isn't established...
            self._df_format = N_labels.copy() # ...Create the format
        ret = await self._device._write_readline("N") # Read the line
        ret = ret.replace("\x00","")
        df = ret.split() # Create a list of every word in the line
        while not 'N' in df[0]: # If the sensor does not output a normal mode line
            print("Error: Gas Card Not in Normal Mode")
            ret = await self._device._write_readline("N") # Read the line again
            ret = ret.replace("\x00","") # Removes '\x00' characters
            df = ret.split() # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index]) # Convert numbers in the list into floats
        # df = clean_mode(df)
        return dict(zip(self._df_format, df)) # Combine the format and the values into a dictionary
    
    async def get_coeff(self) -> str:
        """
        Gets the current value of the device.
        """
        if self._df_format != C1_labels: # If the format isn't established...
            self._df_format = C1_labels.copy() # ...Create the format
        ret = await self._device._write_readline("C1") # Read the line
        ret = ret.replace("\x00","")
        df = ret.split() # Create a list of every word in the line
        while not 'C' in df[0]: # If the sensor does not output a coefficient mode line
            print("Error: Gas Card Not in Coefficient Mode")
            ret = await self._device._write_readline("C1") # Read the line again
            ret = ret.replace("\x00","") # Removes '\x00' characters
            df = ret.split() # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index]) # Convert numbers in the list into floats
        return dict(zip(self._df_format, df)) # Combine the format and the values into a dictionary
    
    async def calibrate(self) -> None:
        """
        Allows user to start calibration routines or change coefficients
        """
        com = input("Enter calibration command (z = zero, s<val> = span, h<val> = 1st coeff, i<val> = 2nd, j<val> = 3rd, k<val> = 4th): ")
        if com.upper() == 'Z':
            input("Press enter once zero gas is flowing")
            await self._device._write_readline("z")
        elif com[0].upper() == 'S':
            while float(com[1:]) < 0.5 or float(com[1:]) > 1.20:
                print("Error: Span value must be between 0.5 and 1.20")
                com = input("Enter calibration command (s<val> = span: ")
            if com[0].upper() != 'S':
                print("Invalid command")
                return
            input("Press enter once span gas is flowing")
            await self._device._write_readline("s" + com[1:])
        elif com[0].upper() == 'H':
            await self._device._write_readline("h" + com[1:])
        elif com[0].upper() == 'I':
            await self._device._write_readline("i" + com[1:])
        elif com[0].upper() == 'J':
            await self._device._write_readline("j" + com[1:])
        elif com[0].upper() == 'K':
            await self._device._write_readline("k" + com[1:])
        else:
            print("Invalid command") # Note the p command hasn't be included
            self.calibrate()
        return

    async def environmental(self) -> str:
        """
        Display and Change Environmental Parameters
        """
        if self._df_format != E1_labels: # If the format isn't established...
            self._df_format = E1_labels.copy() # ...Create the format
        ret = await self._device._write_readline("E1") # Read the line
        ret = ret.replace("\x00","")
        df = ret.split() # Create a list of every word in the line
        while not 'E' in df[0]: # If the sensor does not output an environmental mode line
            print("Error: Gas Card Not in Environmental Mode")
            ret = await self._device._write_readline("E1") # Read the line again
            ret = ret.replace("\x00","") # Removes '\x00' characters
            df = ret.split() # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index]) # Convert numbers in the list into floats
        opt = input("Would you like to change the environmental parameters? Warning: Changing any paramter will lead to incorrect gas sensor operation (y/n): ")
        if opt.upper() == 'Y':
            com = input("Enter calibration command (z<val> = zero temp corr, s<val> = span temp core, g<val> = 1st coeff, e<val> = 2nd, d<val> = 3rd, c<val> = 4th, m<val> =slope corr, x<val> = offset corr): ")
            if com[0].upper() == 'Z':
                ret = await self._device._write_readline("z" + com[1:])
            elif com[0].upper() == 'S':
                ret = await self._device._write_readline("s" + com[1:])
            elif com[0].upper() == 'c':
                ret = await self._device._write_readline("c" + com[1:])
            elif com[0].upper() == 'D':
                ret = await self._device._write_readline("d" + com[1:])
            elif com[0].upper() == 'E':
                ret = await self._device._write_readline("e" + com[1:])
            elif com[0].upper() == 'G':
                ret = await self._device._write_readline("g" + com[1:])
            elif com[0].upper() == 'M':
                ret = await self._device._write_readline("m" + com[1:])
            elif com[0].upper() == 'X':
                ret = await self._device._write_readline("x" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("E1") # Read the line
            ret = ret.replace("\x00","")
            df = ret.split() # Create a list of every word in the line
            while not 'E' in df[0]: # If the sensor does not output an environmental mode line
                print("Error: Gas Card Not in Environmental Mode")
                ret = await self._device._write_readline("E1") # Read the line again
                ret = ret.replace("\x00","") # Removes '\x00' characters
                df = ret.split() # Create a list of every word in the line
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index]) # Convert numbers in the list into floats
        return dict(zip(self._df_format, df)) # Combine the format and the values into a dictionary
    
    async def output(self) -> str:
        """
        Display and Change Environmental Parameters
        """
        if self._df_format != O1_labels: # If the format isn't established...
            self._df_format = O1_labels.copy() # ...Create the format
        ret = await self._device._write_readline("O1") # Read the line
        ret = ret.replace("\x00","")
        df = ret.split() # Create a list of every word in the line
        while not 'O' in df[0]: # If the sensor does not output an output mode line
            print("Error: Gas Card Not in Output Mode")
            ret = await self._device._write_readline("O1") # Read the line again
            ret = ret.replace("\x00","") # Removes '\x00' characters
            df = ret.split() # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index]) # Convert numbers in the list into floats
        opt = input("Would you like to change the output parameters? (y/n): ")
        if opt.upper() == 'Y':
            com = input("Enter calibration command (m<val> = PWM volt output slope cal, x<val> = PWM volt output offset cal, a<val> = PWM current output slope cal, b<val> = PWM current output offset cal, v<val> = volt output range): ")
            if com[0].upper() == 'M':
                ret = await self._device._write_readline("m" + com[1:])
            elif com[0].upper() == 'X':
                ret = await self._device._write_readline("x" + com[1:])
            elif com[0].upper() == 'A':
                ret = await self._device._write_readline("a" + com[1:])
            elif com[0].upper() == 'B':
                ret = await self._device._write_readline("b" + com[1:])
            elif com[0].upper() == 'V':
                ret = await self._device._write_readline("v" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("O1") # Read the line
            ret = ret.replace("\x00","")
            df = ret.split() # Create a list of every word in the line
            while not 'O' in df[0]: # If the sensor does not output an output mode line
                print("Error: Gas Card Not in output Mode")
                ret = await self._device._write_readline("E1") # Read the line again
                ret = ret.replace("\x00","") # Removes '\x00' characters
                df = ret.split() # Create a list of every word in the line
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index]) # Convert numbers in the list into floats
        return dict(zip(self._df_format, df)) # Combine the format and the values into a dictionary
    
    
    async def settings(self) -> str:
        """
        Display and Change Settings
        """
        # **SWITCHES STATE NOT IMPLEMENTED**
        if self._df_format != X_labels:
            self._df_format = X_labels.copy() # ...Create the format
        ret = await self._device._write_readline("X") # Read the line
        ret = ret.replace("\x00","")
        df = ret.split() # Create a list of every word in the line
        while not 'X' in df[0]: # If the sensor does not output a settings mode line
            print("Error: Gas Card Not in Settings Mode")
            ret = await self._device._write_readline("X") # Read the line again
            ret = ret.replace("\x00","") # Removes '\x00' characters
            df = ret.split() # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index]) # Convert numbers in the list into floats
        opt = input("Would you like to change the settings parameters? (y/n): ")
        if opt.upper() == 'Y':
            com = input("Enter calibration command (f<val> = lamp freq [Hz] (1 to 9), t<val> = RC time const, d = reset all sensor variables, q = Soft reset): ")
            if com[0].upper() == 'F':
                opt = input("WARNING: Changing the frequency will change the calibration coefficients. Would you like to continue? (y/n): ")
                if opt.upper() == 'Y':
                    while float(com[1:]) < 1 or float(com[1:]) > 9:
                        print("Error: Frequency must be between 1 and 9")
                        com = input("Enter calibration command (f<val> = lamp freq [Hz] (1 to 9): ")
                    if com[0].upper() != 'F':
                        print("Invalid command")
                        return dict(zip(self._df_format, df))
                    await self._device._write_readline("s" + com[1:])
                    ret = await self._device._write_readline("f" + com[1:])
                else:
                    return dict(zip(self._df_format, df))
            elif com[0].upper() == 'T':
                ret = await self._device._write_readline("t" + com[1:])
            elif com[0].upper() == 'D':
                opt = input("WARNING: This will reset all sensor variables. This will render the sensor useless until re-setup. Would you like to continue? (y/n): ")
                if opt.upper() == 'Y':
                    ret = await self._device._write_readline("d")
            elif com[0].upper() == 'Q':
                ret = await self._device._write_readline("q" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("X") # Read the line
            ret = ret.replace("\x00","")
            df = ret.split() # Create a list of every word in the line
            while not 'X' in df[0]: # If the sensor does not output an settings mode line
                print("Error: Gas Card Not in settings Mode")
                ret = await self._device._write_readline("X") # Read the line again
                ret = ret.replace("\x00","") # Removes '\x00' characters
                df = ret.split() # Create a list of every word in the line
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index]) # Convert numbers in the list into floats
        return dict(zip(self._df_format, df)) # Combine the format and the values into a dictionary

    async def userinterface(self) -> str:
        """
        View user Interface
        """
        if self._df_format != U_labels:
            self._df_format = U_labels.copy() # ...Create the format
        ret = await self._device._write_readline("U") # Read the line
        ret = ret.replace("\x00","")
        df = ret.split() # Create a list of every word in the line
        while not 'U' in df[0]: # If the sensor does not output a user interface mode line
            print("Error: Gas Card Not in User Interface Mode")
            ret = await self._device._write_readline("U") # Read the line again
            ret = ret.replace("\x00","") # Removes '\x00' characters
            df = ret.split() # Create a list of every word in the line
        for index in range(len(df)):
            if df[index].isnumeric():
                df[index] = float(df[index]) # Convert numbers in the list into floats
        opt = input("Would you like to display or test? (y/n): ")
        if opt.upper() == 'Y':
            com = input("Enter command (d<val> = display selection, t = Test LEDs and display): ")
            if com[0].upper() == 'D':
                ret = await self._device._write_readline("d" + com[1:])
            elif com[0].upper() == 'T':
                ret = await self._device._write_readline("t" + com[1:])
            else:
                print("Invalid command")
            # Get the new dictionary, this should be cleaned up no point in repeating code like this
            ret = await self._device._write_readline("X") # Read the line
            ret = ret.replace("\x00","")
            df = ret.split() # Create a list of every word in the line
            while not 'X' in df[0]: # If the sensor does not output an settings mode line
                print("Error: Gas Card Not in settings Mode")
                ret = await self._device._write_readline("X") # Read the line again
                ret = ret.replace("\x00","") # Removes '\x00' characters
                df = ret.split() # Create a list of every word in the line
            for index in range(len(df)):
                if df[index].isnumeric():
                    df[index] = float(df[index]) # Convert numbers in the list into floats
        return dict(zip(self._df_format, df)) # Combine the format and the values into a dictionary


    async def get_df_format(self) -> str:
        """
        Gets the format of the current dataframe format of the device
        """
        resp = await self._device._write_readall(self._id + "??D*") # Call the command to read the device (id + ??D*)
        splits = []
        for match in re.finditer(r"\s", resp[0]): # Breaks first line of output into iterable of match objects for each whitespace
            splits.append(match.start()) # Adds the start index/position of each match object to the list splits
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
