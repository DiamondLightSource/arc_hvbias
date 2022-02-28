"""
Defines a connection to a Kiethley 2400 over serial and provides an interface
to command and query the device
"""

import io

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
        self.send_recv("", False)
        # turn off the BEEP!
        self.send_recv(":syst:beep:stat 0", False)
        # Check the connection
        model = self.send_recv("*idn?")
        if "MODEL 24" not in model:
            raise ValueError(f"Device Identifier not recognized: {model}")

    def __del__(self):
        if hasattr(self, "connection"):
            self.ser.close()

    def send_recv(self, send: str, respond: bool = True) -> str:
        print("send", send)
        self.ser.write((send + "\n").encode())

        if respond:
            response = self.ser.readline(100).decode()
            print("recv", response)
        else:
            self.ser.flush()
            response = ""

        return response
