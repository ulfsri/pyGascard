"""DAQ Class for managing gascard devices. Accessible to external API and internal logging module.

Author: Grayson Bellamy
Date: 2024-01-07
"""

import time
import warnings
from datetime import datetime
from queue import Queue
from threading import Thread
from typing import Any, Callable

import asyncpg
from anyio import create_task_group, run

from pygascard import device

warnings.filterwarnings("always")


class DAQ:
    """Class for managing gascard devices. Accessible to external API and internal logging module. Wraps and allows communication with inidividual or all devices through wrapper class."""

    def __init__(self) -> None:
        """Initializes the DAQ.

        TODO: Pass dictionary of names and addresses to initialize devices. Same async issue.

        """
        self._dev_list: dict[str, device.Gascard] = {}

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
                    self._dev_list.update({name: dev})
                elif isinstance(devs[name], device.Gascard):
                    self._dev_list.update({name: devs[name]})
        return

    async def remove_device(self, name: list[str]) -> None:
        """Removes the devices.

        Args:
            name (list[str]): The list of names of devices to remove.
        """
        for n in name:
            await self._dev_list[n]._device.close()
            del self._dev_list[n]
        return

    async def dev_list(self) -> dict[str, device.Gascard]:
        """Displays the list of devices.

        Returns:
            dict[str, device.Gascard]: The list of devices and their objects.
        """
        return self._dev_list

    async def update_dict_get(
        self,
        ret_dict: dict[str, dict[str, str | float | datetime]],
        dev: str,
        val: list[str],
    ) -> dict[str, dict[str, str | float | datetime]]:
        """Updates the dictionary with the new values.

        Args:
            ret_dict (dict): The dictionary of devices to update.
            dev (str): The name of the device.
            val (list): The values to get from the device.

        Returns:
            dict: The dictionary of devices with the updated values.
        """
        start = datetime.now()
        vals = await self._dev_list[dev].get(val)
        vals.update(
            {
                "Request Sent": start,
                "Response Received": datetime.now(),
            }
        )
        ret_dict.update({dev: vals})
        return ret_dict

    async def get(
        self, val: list[str] | None = None, id: list[str] | None = None
    ) -> dict[str, dict[str, str | float | datetime]]:
        """Gets the data from the device.

        If id not specified, returns data from all devices.

        Example:
            df = run(Daq.get, ["Gas Type", "Gas Range", "Conc 1"], ['A', 'B'])
            df = run(Daq.get, ["Gas Type", "Gas Range", "Conc 1"])
            df = run(Daq.get, ["Gas Type", "Gas Range", "Conc 1"], 'B')
            df = run(Daq.get, "Gas Type")

        Args:
           val (list): The values to get from the device.
           id (list): The IDs of the devices to read from. If not specified, returns data from all devices.

        Returns:
            dict: The dictionary of devices with the data for each value.
        """
        ret_dict: dict[str, dict[str, str | float | datetime]] = {}
        if val and isinstance(val, str):
            val = [val]
        if not id:
            async with create_task_group() as g:
                for dev in self._dev_list:
                    g.start_soon(self.update_dict_get, ret_dict, dev, val)
        else:
            async with create_task_group() as g:
                for i in id:
                    g.start_soon(self.update_dict_get, ret_dict, i, val)
        return ret_dict

    async def update_dict_set(
        self,
        ret_dict: dict[str, dict[str, str | float | datetime]],
        dev: str,
        command: list[str],
    ) -> dict[str, dict[str, str | float]]:
        """Updates the dictionary with the new values.

        Args:
            ret_dict (dict): The dictionary of devices to update.
            dev (str): The name of the device.
            command (list): The command to run on the device.

        Returns:
            dict: The dictionary of devices with the updated values.
        """
        ret_dict.update({dev: await self._dev_list[dev].set(command)})
        return ret_dict

    async def set(
        self, command: dict[str, str | float], id: str | None = None
    ) -> dict[str, dict[str, str | float]] | None:
        """Sets the data of the device.

        Example:
            df = run(Daq.set, {"Setpt": 50})
            df = run(Daq.set, {"Setpt": 50}, ['A', 'B'])
            df = run(Daq.set, {"Setpt": 50}, ["B"])

        Args:
           command (dict): The commands and their relevant parameters to send to the device.
           id (list): The IDs of the devices to read from. If not specified, returns data from all devices.

        Returns:
            dict: The dictionary of devices with the data for each value.
        """
        ret_dict = {}
        if isinstance(command, str):
            command = command.split()
        if not id:
            async with create_task_group() as g:
                for dev in self._dev_list:
                    g.start_soon(self.update_dict_set, ret_dict, dev, command)
        else:
            async with create_task_group() as g:
                for i in id:
                    g.start_soon(self.update_dict_set, ret_dict, i, command)
        return ret_dict

    async def zero(self, id: list[str] | None = None) -> None:
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
        if not id:
            for dev in self._dev_list:
                await self._dev_list[dev].set({"Zero Gas Corr Factor": ""})
        else:
            for i in id:
                await self._dev_list[i].set({"Zero Gas Corr Factor": ""})
        return

    async def span(self, val: float, id: list[str] | None = None) -> None:
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
        if not id:
            for dev in self._dev_list:
                await self._dev_list[dev].set({"Span Gas Corr Factor": val})
        else:
            for i in id:
                await self._dev_list[i].set({"Span Gas Corr Factor": val})
        return

    async def time_const(self, val: int, id: list[str] | None = None) -> None:
        """Sets the time constant of the RC filter of the device.

        Example:
            df = run(Daq.time_const, 0, ['A', 'B'])

        Args:
            val (int): Time constant in seconds (0 to 120)
            id (list[str]): The IDs of the devices to read from. If not specified, returns data from all devices.
        """
        if not id:
            for dev in self._dev_list:
                await self._dev_list[dev].time_const(val)
        else:
            for i in id:
                await self._dev_list[i].time_const(val)
        return


class AsyncPG:
    """Async context manager for connecting to a PostgreSQL database using asyncpg."""

    def __init__(self, **kwargs):
        """Initializes the AsyncPG object."""
        self.conn = asyncpg.Connection | None
        self.kwargs = kwargs

    async def __aenter__(self):
        """Enters the async context manager and connects to the database."""
        self.conn = await asyncpg.connect(**self.kwargs)
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        """Exits the async context manager and closes the connection to the database."""
        if self.conn:
            await self.conn.close()
        self.conn = None


class DAQLogging:
    """Class for logging the data from Gascard devices. Creates and saves file to disk with given acquisition rate. Only used for standalone logging. Use external API for use as plugin."""

    def __init__(
        self, Daq: DAQ, qualities: list[str], rate: float, database: str
    ) -> None:
        """Initializes the Logging module.

        Note:
            Gascard devices have upper limit rate of 8 Hz.

        Example:
            log = run(daq.DAQLogging.init, Daq, [], 10, 'test.csv')

        Args:
            Daq (DAQ): The DAQ object to take readings from.
            qualities (list): The list of qualities to log.
            rate (float): The rate at which to log the data in Hz.
            database (str): The name of the database to save the data to.
        """
        self.Daq = Daq
        self.qualities = qualities
        self.rate = rate
        self.database = AsyncPG(
            user="app", password="app", database="app", host="127.0.0.1"
        )
        self.qin: Queue[str | Callable | list[Callable | Any]] | None = None
        self.qout: Queue[str | float] | None = None
        return

    def _key_func(self, x):
        if x == "Request Sent":
            return chr(0)
        if x == "Response Received":
            return chr(1)
        if x.lower() == "mode":
            return chr(2)
        return x

    async def create_table(self, dict, conn):
        """Creates a table in the database and adds columns for each key in the dictionary.

        Args:
            dict (dict): The dictionary containing the data to be added as columns.
            conn: The connection object to the database.
        """
        async with conn.transaction():
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS gascard (Time timestamp, Device text, PRIMARY KEY (Time, Device))"
            )
            keys = sorted(dict.keys(), key=self._key_func)
            for key in keys:
                data_type = "text"
                if key == "Request Sent" or key == "Response Received":
                    data_type = "timestamp"
                elif isinstance(dict[key], float):
                    data_type = "float"
                await conn.execute(
                    f"ALTER TABLE gascard ADD COLUMN IF NOT EXISTS {''.join(key.split()).lower()} {data_type}"
                )
            await conn.execute(
                "SELECT create_hypertable('gascard', by_range('time'), if_not_exists => TRUE)"
                # create the timescaledb hypertable
            )

    async def insert_data(self, dict, conn):
        """Inserts the data into the database.

        Args:
            dict (dict): The dictionary containing the data to be added.
            conn: The connection object to the database.
        """
        async with conn.transaction():
            for dev in dict:
                await conn.execute(
                    "INSERT INTO gascard ("
                    + ", ".join([key.lower().replace(" ", "") for key in dev.keys()])
                    + ") VALUES ("
                    + ", ".join(["$" + str(i + 1) for i in range(len(dev))])
                    + ")",
                    *dev.values(),
                    # We could optimize this by using a single insert statement for all devices. We would have to make sure that the order of the values is the same for all devices and it would only work if they all have the same fields. That is, it wouldn't work for the flowmeter in our case because it has RH values
                )

    async def update_dict_log(self, Daq: DAQ, qualities: list[str]) -> None:
        """Updates the dictionary with the new values.

        Args:
            Daq (DAQ): The DAQ object to take readings from.
            qualities (list): The list of qualities to log.
        """
        self.df = await Daq.get(qualities)
        return

    async def logging(
        self,
        write_async: bool = False,
        duration: float | None = None,
        rate: float | None = None,
    ) -> None:
        """Initializes the Logging module. Creates and saves file to disk with given acquisition rate.

        Args:
            write_async (bool): Whether to write the data asynchronously.
            duration (float): The duration to log the data in seconds.
            rate (float): The rate at which to log the data in Hz.
        """
        if not duration:
            duration = 610000  # If no duration is specified, run for over 1 week
        if not rate:
            rate = self.rate
        database = self.database
        rows = []
        async with database as conn:
            self.df = await self.Daq.get(self.qualities)
            unique = dict()
            for dev in self.df:
                unique.update(self.df[dev])
            await self.create_table(unique, conn)
            start = time.perf_counter_ns()
            prev = start
            reps = 0
            while (time.perf_counter_ns() - start) / 1e9 <= duration:
                # Check if something in queue
                if not self.qin.empty():
                    comm = self.qin.get()
                    # if stop_logging is in the queue, break out of the while loop
                    if comm == "Stop":
                        break
                    elif isinstance(comm, list) and isinstance(comm[0], function):
                        df = await comm[0](*comm[1:])
                        self.qout.put(df)
                # if not, continue logging
                if time.time_ns() / 1e9 - (reps * 1 / rate + start / 1e9) >= 1 / rate:
                    # Check if something is in the queue
                    # print(
                    #     f"Difference between readings: {(time.time_ns() - prev) / 1e9} s"
                    # )
                    # if (
                    #     abs(time.time_ns() / 1e9 - reps * 1 / rate - start / 1e9)
                    #     > 1.003 / rate
                    # ):
                    #     warnings.warn("Warning! Acquisition rate is too high!")
                    time1 = time.perf_counter_ns()
                    prev = time.perf_counter_ns()
                    if write_async:
                        nurse_time = time.perf_counter_ns()
                        # open_nursery
                        async with create_task_group() as g:
                            # insert_data from the previous iteration
                            g.start_soon(self.insert_data, rows, conn)
                            # get
                            g.start_soon(self.update_dict_log, self.Daq, self.qualities)
                    else:
                        nurse_time = time.perf_counter_ns()
                        # Get the data
                        self.df = await self.Daq.get(self.qualities)
                        # Write the data from this iteration
                    time2 = time.perf_counter_ns()
                    rows = []
                    for dev in self.df:
                        rows.append(
                            {
                                "Time": (
                                    self.df[dev]["Request Sent"]
                                    + (
                                        self.df[dev]["Response Received"]
                                        - self.df[dev]["Request Sent"]
                                    )
                                    / 2
                                ),
                                "Device": dev,
                                "Request Sent": self.df[dev]["Request Sent"],
                                "Response Received": self.df[dev]["Response Received"],
                                **self.df[dev],
                            }
                        )
                    # print(f"Process took {(time2 - time1) / 1e6} ms")
                    time3 = time.perf_counter_ns()
                    if not write_async:
                        await self.insert_data(
                            rows, conn
                        )  # This takes a little bit (~8 ms). I think we should run this in a nursery with the next .get() call. That means that we will have to wait until the next loop to submit the data from the previous iteration.
                    time4 = time.perf_counter_ns()
                    # print(f"Insert took {(time4 - time3) / 1e6} ms")
                    print(f"Time with nursery is {(time4 - nurse_time) / 1e6} ms")
                    reps += 1
                    while (time.perf_counter_ns() - start) / 1e9 / (
                        1 / rate
                    ) >= 1.00 * reps + 1:
                        reps += 1
                        warnings.warn("Warning! Process takes too long!")
            print(
                f"Total time: {(time.perf_counter_ns() - start) / 1e9} s with {reps} reps"
            )

    def start_logging(
        self,
        write_async: bool = False,
        duration: float | None = None,
        rate: float | None = None,
    ) -> tuple[Queue[str | Callable | list[Callable | Any]], Queue[str | float]]:
        """Starts the logging process.

        Example:
            qin, qout = Log.start_logging(True, 30, 1)

        Args:
            write_async (bool): Whether to write the data asynchronously.
            duration (float): The duration to log the data in seconds.
            rate (float): The rate at which to log the data in Hz.

        Returns:
            tuple[Queue, Queue]: The input and output queues for the logging process.
        """
        # Create the queue
        self.qin = Queue()
        self.qout = Queue()
        backend_options = {"use_uvloop": True}
        # Start the logging process in a thread
        t = Thread(
            target=run,
            args=(self.logging, write_async, duration, rate),
            kwargs={"backend_options": backend_options},
        )
        t.start()
        # Return the queue
        return (self.qin, self.qout)

    async def stop_logging(self):
        """Stops the logging process.

        Example:
            run(Log.stop_logging)
        """
        # Needs to save the data into the file
        # Delete table in database?
        self.qin.put("Stop")
        return

    async def q_t(self, state1, state2):
        """Test function for the DAQLogging class."""
        print(f"State 1 = {state1}")
        print(f"State 2 = {state2}")
        time.sleep(10)
        return

    async def set(self, *args):
        """Set function for the DAQLogging class.

        Example:
            df = run(Log.set, {"Time_Constant":1}, "/dev/ttyUSB4")

        Args:
            *args: The arguments to pass to the set function.
        """
        self.qin.put([self.Daq.set, *args])
        return self.qout.get()

    async def get(self, *args):
        """Get function for the DAQLogging class.

        Example:
            df = run(Log.get, "Temperature")

        Args:
            *args: The arguments to pass to the get function.
        """
        self.qin.put([self.Daq.get, *args])
        return self.qout.get()
