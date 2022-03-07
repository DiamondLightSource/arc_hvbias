"""
Defines a connection to a Kiethley 2400 over serial and provides an interface
to command and query the device
"""
import math

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

        # Check the connection
        self.send_recv("")
        model = self.send_recv("*idn?")
        if "MODEL 24" not in model:
            raise ValueError(f"Device Identifier not recognized: {model}")
        print(f"connected to: {model}")

        # set up useful defaults
        self.send_recv(":syst:beep:stat 0")  # no beeps !!!
        self.send_recv(":SOURCE:VOLTAGE:RANGE:AUTO 1")
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

    def source_off(self):
        self.send_recv(":SOURCE:CLEAR:IMMEDIATE")

    def source_on(self):
        self.send_recv(":OUTPUT:STATE ON")

    def get_source_status(self) -> int:
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

    def voltage_sweep(self, to_volts: float, step_size: float, seconds: float):
        start = self.get_voltage()
        change = to_volts - start
        step_count = change / step_size
        delay = seconds / step_count
        cmd = self.sweep_commands.format(**locals())
        self.send_recv(cmd)
        # Complete the sweep as above gets to within 1 step of to_volts
        cothread.Sleep(delay)
        self.set_voltage(to_volts)

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
:INIT"""
