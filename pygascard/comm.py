"""Sets up the communication for the gas card device.

Author: Grayson Bellamy
Date: 2024-01-05
"""

from typing import Optional
from collections.abc import ByteString

from abc import ABC, abstractmethod

import trio
from trio_serial import Parity, SerialStream, StopBits


class CommDevice(ABC):
    """Sets up the communication for the an Alicat device."""

    def __init__(self, timeout: int) -> None:
        """Initializes the serial communication.

        Args:
            timeout (int): The timeout of the Alicat device.
        """
        self.timeout = timeout

    @abstractmethod
    async def _read(self, len: int) -> Optional[str]:
        """Reads the serial communication.

        Args:
            len (int): The length of the serial communication to read. One character if not specified.

        Returns:
            str: The serial communication.
        """
        pass

    @abstractmethod
    async def _write(self, command: str) -> None:
        """Writes the serial communication.

        Args:
            command (str): The serial communication.
        """
        pass

    @abstractmethod
    async def close(self):
        """Closes the serial communication."""
        pass

    @abstractmethod
    async def _readline(self) -> Optional[str]:
        """Reads the serial communication until end-of-line character reached.

        Returns:
            str: The serial communication.
        """
        pass

    @abstractmethod
    async def _write_readline(self, command: str) -> Optional[str]:
        """Writes the serial communication and reads the response until end-of-line character reached.

        Args:
            command (str): The serial communication.

        Returns:
            str: The serial communication.
        """
        pass


class SerialDevice(CommDevice):
    """Sets up the communication for the a gas card device using serial protocol."""

    def __init__(  # Need to verify Flow Control is set to 'none'
        self,
        port: str,
        baudrate: int = 57600,
        timeout: int = 150,  # Not present in manual
        databits: int = 8,
        parity: Parity = Parity.NONE,
        stopbits: StopBits = StopBits.ONE,
        xonxoff: bool = False,  # Not present in manual
        rtscts: bool = False,  # Not present in manual
        exclusive: bool = False,  # Not present in manual
    ):
        """Initializes the serial communication.

        Args:
            port (str): The port to which the Alicat device is connected.
            baudrate (int): The baudrate of the Alicat device.
            timeout (int): The timeout of the Alicat device in ms.
            databits (int): The number of data bits.
            parity (Parity): The parity of the Alicat device.
            stopbits (StopBits): The of stop bits. Usually 1 or 2.
            xonxoff (bool): Whether the port uses xonxoff.
            rtscts (bool): Whether the port uses rtscts.
            exclusive (bool): Whether the port is exclusive.
        """
        super().__init__(timeout)

        self.timeout = timeout
        self.eol = b"\r"
        self.serial_setup = {
            "port": port,
            "exclusive": exclusive,
            "baudrate": baudrate,
            "bytesize": databits,
            "parity": parity,
            "stopbits": stopbits,
            "xonxoff": xonxoff,
            "rtscts": rtscts,
        }
        self.isOpen = False
        self.ser_devc = SerialStream(**self.serial_setup)

    async def _read(self, len: int = 1) -> ByteString:
        """Reads the serial communication.

        Args:
            len (int): The length of the serial communication to read. One character if not specified.

        Returns:
            ByteString: The serial communication.
        """
        if not self.isOpen:
            async with self.ser_devc:
                with trio.move_on_after(self.timeout / 1000):
                    return await self.ser_devc.receive_some(len)
        else:
            with trio.move_on_after(self.timeout / 1000):
                return await self.ser_devc.receive_some(len)
        return None

    async def _write(self, command: str) -> None:
        """Writes the serial communication.

        Args:
            command (str): The serial communication.
        """
        if not self.isOpen:
            async with self.ser_devc:
                with trio.move_on_after(self.timeout / 1000):
                    await self.ser_devc.send_all(command.encode("ascii") + self.eol)
        else:
            with trio.move_on_after(self.timeout / 1000):
                await self.ser_devc.send_all(command.encode("ascii") + self.eol)
        return None

    async def _readline(self) -> str:
        """Reads the serial communication until end-of-line character reached.

        Returns:
            str: The serial communication.
        """
        async with self.ser_devc:
            self.isOpen = True
            line = bytearray()
            c = None
            while (
                c != self.eol
            ):  # Keep reading until end-of-line character reached, then we know new line is started
                c = await self._read(1)
            while True:
                c = None
                with trio.move_on_after(self.timeout / 1000):
                    c = await self._read(1)
                    line += c
                    if c == self.eol:
                        break
                if c is None:
                    break
        self.isOpen = False
        return line.decode("ascii")

    async def _write_readall(self, command: str) -> list:
        """Write command and read until timeout reached.

        Args:
            command (str): The serial communication.

        Returns:
            list: List of lines read from the device.
        """
        async with self.ser_devc:
            self.isOpen = True
            await self._write(command)
            line = bytearray()
            arr_line = []
            await self._flush()
            while True:
                c = None
                with trio.move_on_after(self.timeout / 1000):
                    c = await self._read(1)
                    if c == self.eol:
                        arr_line.append(line.decode("ascii"))
                        line = bytearray()
                    else:
                        line += c
                if c is None:
                    break
        self.isOpen = False
        return arr_line

    async def _write_readline(self, command: str) -> str:
        """Writes the serial communication and reads the response until end-of-line character reached.

        Parameters:
            command (str): The serial communication.

        Returns:
            str: The serial communication.
        """
        async with self.ser_devc:
            self.isOpen = True
            await self._write(command)
            line = bytearray()
            c = None
            while (
                c != self.eol and c is not None
            ):  # Keep reading until end-of-line character reached, then we know new line is started
                c = await self._read(1)
            while True:
                c = None
                with trio.move_on_after(self.timeout / 1000):
                    c = await self._read(1)
                    if c == self.eol:
                        break
                    line += c
                if c is None:
                    break
        self.isOpen = False
        return line.decode("ascii")

    async def _flush(self) -> None:
        """Flushes the serial communication."""
        await self.ser_devc.discard_input()

    async def close(self) -> None:
        """Closes the serial communication."""
        self.isOpen = False
        await self.ser_devc.aclose()

    async def open(self) -> None:
        """Opens the serial communication."""
        self.isOpen = True
        await self.ser_devc.aopen()
