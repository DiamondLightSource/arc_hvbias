from enum import IntEnum


class Status(IntEnum):
    VOLTAGE_OFF = 0
    VOLTAGE_ON = 1
    RAMP_UP = 2
    HOLD = 3
    RAMP_DOWN = 4
    ERROR = 5
