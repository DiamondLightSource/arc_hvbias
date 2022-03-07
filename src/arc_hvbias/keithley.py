"""
Defines a connection to a Kiethley 2400 over serial and provides an interface
to command and query the device
"""
import math
from datetime import datetime

import cothread
import serial


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
        if self.sweep_test():
            # TODO
            volts = "66"
        else:
            volts = self.send_recv(":SOURCE:VOLTAGE?")
        return float(volts)

    def set_voltage(self, volts: float):
        # only allow negative voltages
        volts = math.fabs(volts) * -1
        return self.send_recv(f":SOURCE:VOLTAGE {volts}")

    def get_current(self) -> float:
        if self.sweep_test():
            # We have no way of determining Amps during a sweep
            amps = "0"
        else:
            amps = self.send_recv(":SOURCE:CURRENT?")
        # make it mAmps
        return float(amps) * 1000

    def source_off(self):
        self.send_recv(":SOURCE:CLEAR:IMMEDIATE")

    def source_on(self):
        self.send_recv(":OUTPUT:STATE ON")

    def get_source_status(self) -> int:
        if self.sweep_test():
            # power must be on during a sweep
            result = "1"
        else:
            result = self.send_recv(":OUTPUT:STATE?")
        return int(result)

    def source_voltage_ramp(
        self, start: float, stop: float, steps: int, seconds: float
    ) -> None:
        voltage = start
        self.send_recv(":SOURCE:FUNCTION:MODE VOLTAGE")
        self.send_recv(":SOURCE:VOLTAGE:MODE FIXED")
        for step in range(steps + 1):
            self.send_recv(f":SOURCE:VOLTAGE {voltage}")
            self.get_voltage()
            voltage += (stop - start) / steps
            cothread.Sleep(seconds / steps)

    def sweep_test(self):
        """
        Looks for the operation complete signal during a sweep
        and returns true if currently in a sweep
        """
        sweeping = False
        if self.sweep_seconds > 0:
            time_since = (datetime.now() - self.sweep_start).total_seconds()
            if time_since > self.sweep_seconds:
                # check for Operation Complete
                result = self.ser.readline(5).decode()
                # we ares still sweeping if we have not received the "1"
                # from *OPC? and 10 sec timeout has not expired
                sweeping = result != "1" and time_since - self.sweep_seconds < 10
                if not sweeping:
                    self.sweep_seconds = 0
        return sweeping

    def sweep_volts(self):
        """
        returns an estimate of the current voltage during a sweep or 0
        if there is no sweep
        """
        time_since = (datetime.now() - self.sweep_start).total_seconds()
        if time_since > self.sweep_seconds:
            result = 0
        else:
            # TODO this is incorrect - but we may not need this if
            # we can read the sense instead of output
            result = time_since / self.sweep_seconds
        print(result)
        return result

    def voltage_sweep(self, to_volts: float, step_size: float, seconds: float):

        # IMPORTANT: this device cannot be polled while doing a sweep. You
        # can program it to take readings during the sweep but they are only
        # delivered at the end. THEREFOR we must suppress polling during a
        # sweep or we will get input buffer overruns and errors from all polls.

        start = self.get_voltage()
        change = to_volts - start
        step_count = int(change / step_size)
        # alter step size exactly fit into the range
        step_size = change / step_count
        delay = seconds / step_count
        cmd = self.sweep_commands.format(**locals())

        # setup sweep
        self.send_recv(cmd)
        # these class properties track when we can start polling again
        self.sweep_start = datetime.now()
        self.sweep_seconds = seconds

    startup_commands = """
:syst:beep:stat 0
:SOURCE:VOLTAGE:RANGE:AUTO 1
:SENSE:FUNCTION:ON VOLTAGE CURRENT
:SENSE:CURRENT:RANGE AUTO
:SENSE:VOLTAGE:RANGE AUTO
"""

    sweep_commands = """
:SOURCE:FUNCTION:MODE VOLTAGE
:SOURCE:VOLTAGE:MODE SWEEP
:SOURCE:SWEEP:SPACING LINEAR
:SOURCE:VOLTAGE:RANGE:AUTO 1
:SOURCE:VOLTAGE:START {start}
:SOURCE:VOLTAGE:STOP {to_volts}
:SOURCE:VOLTAGE:STEP {step_size}
:TRIGGER:CLEAR
:TRIGGER:SEQ1:COUNT {step_count}
:TRIGGER:SEQ1:DELAY {delay}
:TRIGGER:SEQ1:SOURCE IMMEDIATE
:OUTPUT:STATE ON
:INIT
:OPC?"""
