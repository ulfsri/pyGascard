"""Sets up the communication for the gas card device.

Author: Grayson Bellamy
Date: 2024-01-05
"""

from abc import ABC, abstractmethod
from collections.abc import ByteString

import anyio
import anyio.lowlevel
from anyserial import SerialStream
from anyserial.abstract import Parity, StopBits


class CommDevice(ABC):
    """Sets up the communication for the an Alicat device."""

    def __init__(self, timeout: int) -> None:
        """Initializes the serial communication.

        Args:
            timeout (int): The timeout of the Alicat device.
        """
        self.timeout = timeout

    @abstractmethod
    async def _read(self, len: int) -> str | None:
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
    async def _readline(self) -> str | None:
        """Reads the serial communication until end-of-line character reached.

        Returns:
            str: The serial communication.
        """
        pass

    @abstractmethod
    async def _write_readline(self, command: str) -> str | None:
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
        self.eol = b"\r\n"
        self.serial_setup = {
            "port": port,
            "exclusive": exclusive,
            "baudrate": baudrate,
            "bytesize": databits,
            "parity": parity,
            "stopbits": stopbits,
            # "xonxoff": xonxoff,
            # "rtscts": rtscts,
        }
        self.isOpen = False
        self.ser_devc = SerialStream(**self.serial_setup)
        self.codes_list = [
            bytearray("N ", "ascii"),
            bytearray("N1 ", "ascii"),
            bytearray("C1 ", "ascii"),
            bytearray("E1 ", "ascii"),
            bytearray("O1 ", "ascii"),
            bytearray("X ", "ascii"),
            bytearray("U ", "ascii"),
        ]

    async def _read(self, len: int = None) -> ByteString:
        """Reads the serial communication.

        Args:
            len (int): The length of the serial communication to read. One character if not specified.

        Returns:
            ByteString: The serial communication.
        """
        if len is None:
            len = self.ser_devc.in_waiting()
            if len == 0:
                return None
        if not self.isOpen:
            async with self.ser_devc:
                return await self.ser_devc.receive_some(len)
        else:
            return await self.ser_devc.receive_some(len)
        return None

    async def _write(self, command: str) -> None:
        """Writes the serial communication.

        Note: Can writing ever actually timeout?

        Args:
            command (str): The serial communication.
        """
        if not self.isOpen:
            async with self.ser_devc:
                with anyio.move_on_after(self.timeout / 1000):
                    await self.ser_devc.send_all(command.encode("ascii") + self.eol)
        else:
            with anyio.move_on_after(self.timeout / 1000):
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
            while True:  # Keep reading until end-of-line character reached, then we know new line is started
                c = None
                with anyio.move_on_after(
                    self.timeout / 1000
                ):  # if keep reading none, then timeout
                    while c is None:  # Keep reading until a character is read
                        c = await self._read()
                        await anyio.lowlevel.checkpoint()
                if c is None:  # if we reach timeout,
                    break
                line += c
                if line.startswith(
                    tuple(self.codes_list)
                ):  # This is a case where we started reading at the beginning of a new line
                    break
                if (
                    self.eol in line
                ):  # This is a case where we started reading in the middle of a line
                    line = bytearray()
                    break
            while True:
                if c is None:  # if we reach timeout, quit
                    break
                if self.eol in line:  # We already have a full line
                    break
                c = None
                with anyio.move_on_after(
                    self.timeout / 1000
                ):  # if keep reading none, then timeout
                    while c is None:  # Keep reading until a character is read
                        c = await self._read()
                        await anyio.lowlevel.checkpoint()
                line += c
        self.isOpen = False
        return line.decode("ascii")

    # async def _write_readall(self, command: str) -> list:
    #     """Write command and read until timeout reached.

    #     Args:
    #         command (str): The serial communication.

    #     Returns:
    #         list: List of lines read from the device.
    #     """
    #     async with self.ser_devc:
    #         self.isOpen = True
    #         await self._write(command)
    #         line = bytearray()
    #         arr_line = []
    #         await self._flush()
    #         while True:
    #             c = None
    #             with anyio.move_on_after(self.timeout / 1000):
    #                 c = await self._read(1)
    #                 if c == self.eol:
    #                     arr_line.append(line.decode("ascii"))
    #                     line = bytearray()
    #                 else:
    #                     line += c
    #             if c is None:
    #                 break
    #     self.isOpen = False
    #     return arr_line

    async def _write_readline(self, command: str) -> str:
        """Writes the serial communication and reads the response until end-of-line character reached.

        Parameters:
            command (str): The serial communication.

        Returns:
            str: The serial communication.
        """
        async with self.ser_devc:
            self.isOpen = True
            self._write(command)
            line = bytearray()
            while True:  # Keep reading until end-of-line character reached, then we know new line is started
                c = None
                with anyio.move_on_after(
                    self.timeout / 1000
                ):  # if keep reading none, then timeout
                    while c is None:  # Keep reading until a character is read
                        c = await self._read()
                        await anyio.lowlevel.checkpoint()
                if c is None:  # if we reach timeout,
                    break
                line += c
                if line.startswith(
                    tuple(self.codes_list)
                ):  # This is a case where we started reading at the beginning of a new line
                    break
                if (
                    self.eol in line
                ):  # This is a case where we started reading in the middle of a line
                    line = bytearray()
                    break
            while True:
                if c is None:  # if we reach timeout, quit
                    break
                if self.eol in line:  # We already have a full line
                    break
                c = None
                with anyio.move_on_after(
                    self.timeout / 1000
                ):  # if keep reading none, then timeout
                    while c is None:  # Keep reading until a character is read
                        c = await self._read()
                        await anyio.lowlevel.checkpoint()
                line += c
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
