"""
Defines a connection to a Kiethley 2400 over serial and provides an interface
to command and query the device
"""
import math
from datetime import datetime

import cothread
import serial

MAX_HZ = 20
LOOP_OVERHEAD = 0.03


class Keithley(object):
    def __init__(
        self,
        port: str = "/dev/ttyS0",
        baud: int = 34800,
        bytesize: int = 8,
        parity: str = "N",
    ):
        self.ser = serial.Serial(
            port, baud, bytesize=bytesize, parity=parity, timeout=1
        )

        self.sweep_start = datetime.now()
        self.sweep_seconds = 0.0
        self.abort_flag = False

        # Check the connection
        self.send_recv("")
        self.send_recv("*RST")
        model = self.send_recv("*idn?")
        if "MODEL 24" not in model:
            raise ValueError(f"Device Identifier not recognized: {model}")
        print(f"connected to: {model}")

        # set up useful defaults
        self.send_recv(self.startup_commands)
        self.last_recv = ""

    def __del__(self):
        if hasattr(self, "connection"):
            self.ser.close()

    def send_recv(self, send: str, respond: bool = False) -> str:
        self.ser.write((send + "\n").encode())

        if respond or send.endswith("?"):
            self.last_recv = self.ser.readline(100).decode()
            response = self.last_recv
            self.ser.flush()
        else:
            self.ser.flush()
            response = ""

        return response

    def get_voltage(self) -> float:
        volts = self.send_recv(":SOURCE:VOLTAGE?")
        return float(volts)

    def set_voltage(self, volts: float):
        # only allow negative voltages
        volts = math.fabs(volts) * -1
        return self.send_recv(f":SOURCE:VOLTAGE {volts}")

    def get_current(self) -> float:
        amps = self.send_recv(":SOURCE:CURRENT?")
        # make it mAmps
        return float(amps) * 1000

    def source_off(self, _):
        self.send_recv(":SOURCE:CLEAR:IMMEDIATE")

    def source_on(self, _):
        self.send_recv(":OUTPUT:STATE ON")

    def abort(self):
        self.send_recv(":ABORT")
        # come out of sweep mode if we are in it
        self.sweep_seconds = 0
        self.abort_flag = True

    def get_source_status(self) -> int:
        result = self.send_recv(":OUTPUT:STATE?")
        return int(result)

    def source_voltage_ramp(self, to_volts: float, step_size: float, seconds: float):
        cothread.Spawn(self.voltage_ramp_worker, *(to_volts, step_size, seconds))

    def voltage_ramp_worker(
        self, to_volts: float, step_size: float, seconds: float
    ) -> None:
        """
        A manual voltage ramp using immediate commands

        This has the benefit of being able to get readbacks during
        the ramp. But the downside is that it cannot be particularly
        fine grained. 20Hz updates is about the limit.

        The alternative is voltage_sweep but that has all sorts of
        issues that are yet to be fixed
        """
        self.abort_flag = False
        voltage = self.get_voltage()
        # only allow negative values
        to_volts = -math.fabs(to_volts)
        difference = to_volts - voltage
        if difference == 0 or seconds <= 0:
            return

        # calculate steps and step_size but limit to 20Hz
        steps = abs(int(difference / step_size))
        if steps / seconds > MAX_HZ:
            steps = int(seconds * MAX_HZ)
        step_size = difference / steps
        interval = seconds / steps - LOOP_OVERHEAD

        self.send_recv(":SOURCE:FUNCTION:MODE VOLTAGE")
        self.send_recv(":SOURCE:VOLTAGE:MODE FIXED")
        for step in range(steps + 1):
            if self.abort_flag:
                break
            self.send_recv(f":SOURCE:VOLTAGE {voltage}")
            self.get_voltage()
            voltage += step_size
            cothread.Sleep(interval)

    startup_commands = """
:syst:beep:stat 0
:SENSE:FUNCTION:ON  "CURRENT:DC","VOLTAGE:DC"
:SENSE:CURRENT:RANGE:AUTO 1
:SENSE:VOLTAGE:RANGE:AUTO 1
:SOURCE:VOLTAGE:RANGE:AUTO 1
"""
