"""
Defines a connection to a Kiethley 2400 over serial and provides an interface
to command and query the device
"""
from distutils.command.config import LANG_EXT

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
        self.send_recv("")
        # turn off the BEEP!
        self.send_recv(":syst:beep:stat 0")
        # Check the connection
        model = self.send_recv("*idn?")
        if "MODEL 24" not in model:
            raise ValueError(f"Device Identifier not recognized: {model}")
        print(f"connected to: {model}")

    def __del__(self):
        if hasattr(self, "connection"):
            self.ser.close()

    def send_recv(self, send: str, respond: bool = False) -> str:
        print(f"send {send}")
        self.ser.write((send + "\n").encode())

        if respond or send.endswith("?"):
            response = self.ser.readline(100).decode()
        else:
            self.ser.flush()
            response = ""

        return response

    def get_voltage(self) -> str:
        return self.send_recv(":SOURCE:VOLTAGE?")

    def set_voltage(self, volts: float) -> str:
        return self.send_recv(f":SOURCE:VOLTAGE {volts}")

    def get_current(self) -> str:
        return self.send_recv(":SOURCE:CURRENT?")

    def source_off(self):
        self.send_recv(":SOURCE:CLEAR:IMMEDIATE")

    def source_on(self):
        self.send_recv(":OUTPUT:STATE ON")

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
            cothread.sleep(seconds / steps)
