import math
from datetime import datetime
from enum import IntEnum

import cothread

# Import the basic framework components.
from softioc import builder, softioc

from .keithley import Keithley


class Status(IntEnum):
    VOLTAGE_OFF = 0
    VOLTAGE_ON = 1
    RAMP_UP = 2
    HOLD = 3
    RAMP_DOWN = 4
    ERROR = 5


class Ioc:
    """
    A Soft IOC to provide the PVs to control and monitor the Keithley class
    """

    def __init__(self):
        # connect to the Keithley via serial
        self.k = Keithley()

        # Set the record prefix
        builder.SetDeviceName("BL15J-EA-HV-01")

        # Create some output records (for IOC readouts)
        self.cmd_ramp_off = builder.boolOut(
            "RAMP-OFF", always_update=True, on_update=self.do_ramp_off
        )
        self.cmd_ramp_on = builder.boolOut(
            "RAMP-ON", always_update=True, on_update=self.do_ramp_on
        )
        self.cycle = builder.boolOut(
            "CYCLE", always_update=True, on_update=self.do_start_cycle
        )
        self.cmd_stop = builder.boolOut(
            "STOP", always_update=True, on_update=self.do_stop
        )
        self.cmd_output = builder.boolOut(
            "OUTPUT", always_update=True, on_update=self.do_output
        )
        self.cmd_voltage = builder.aOut(
            "VOLTAGE", always_update=True, on_update=self.k.set_voltage
        )
        self.voltage_rbv = builder.aIn("VOLTAGE_RBV", EGU="Volts")
        self.current_rbv = builder.aIn("CURRENT_RBV", EGU="mA", PREC=4)
        self.output_rbv = builder.mbbIn("OUTPUT_RBV", "OFF", "ON")
        self.status_rbv = builder.mbbIn("STATUS", *Status.__members__)
        self.healthy_rbv = builder.mbbIn("HEALTHY_RBV", "UNHEALTHY", "HEALTHY")
        self.cycle_rbv = builder.mbbIn("CYCLE_RBV", "IDLE", "RUNNING")
        self.time_since_rbv = builder.longIn("TIME-SINCE", EGU="Sec")

        # create some input records (for IOC inputs)
        self.on_setpoint = builder.aOut("ON-SETPOINT", initial_value=500, EGU="Volts")
        self.off_setpoint = builder.aOut("OFF-SETPOINT", EGU="Volts")
        self.rise_time = builder.aOut(
            "RISE-TIME", initial_value=0.25, EGU="Sec", PREC=2
        )
        self.hold_time = builder.aOut("HOLD-TIME", initial_value=1, EGU="Sec", PREC=2)
        self.fall_time = builder.aOut("FALL-TIME", initial_value=0.2, EGU="Sec", PREC=2)
        self.pause_time = builder.aOut("PAUSE-TIME", EGU="Sec", PREC=2)
        self.repeats = builder.longOut("REPEATS", initial_value=1)
        self.step_size = builder.aOut("STEP-SIZE", initial_value=5.0)
        self.max_time = builder.longOut("MAX-TIME", initial_value=900)

        # other state variables
        self.last_time = datetime.now()
        self.last_transition = datetime.now()

        # Boilerplate get the IOC started
        builder.LoadDatabase()
        softioc.iocInit()

        cothread.Spawn(self.update)
        # Finally leave the IOC running with an interactive shell.
        softioc.interactive_ioc(globals())

    # main update loop
    def update(self):
        while True:
            try:
                self.voltage_rbv.set(self.k.get_voltage())
                self.current_rbv.set(self.k.get_current())
                self.output_rbv.set(self.k.get_source_status())

                # calculate housekeeping readbacks
                healthy = self.output_rbv.get() == 1 and math.fabs(
                    self.voltage_rbv.get()
                ) == math.fabs(self.on_setpoint.get())
                self.healthy_rbv.set(healthy)

                if self.voltage_rbv.get() == -math.fabs(self.off_setpoint.get()):
                    self.last_time = datetime.now()
                since = (datetime.now() - self.last_time).total_seconds()
                self.time_since_rbv.set(int(since))

                if self.cycle_rbv.get() == 1:
                    self.cycle_control()

                # update loop at 2 Hz
                cothread.Sleep(0.5)
            except ValueError as e:
                # catch conversion errors when device returns and error string
                print(e, self.k.last_recv)

    def cycle_control(self):
        # this function implements a trivial state machine controlled
        # by self.status_rbv
        if self.status_rbv == Status.VOLTAGE_ON:
            pass
        elif self.status_rbv == Status.RAMP_UP:
            pass
        elif self.status_rbv == Status.RAMP_DOWN:
            pass
        elif self.status_rbv == Status.VOLTAGE_OFF:
            pass

    def do_output(self, on_off: bool):
        if on_off:
            self.k.source_on()
        else:
            self.k.source_off()

    def set_voltage(self, volts: str):
        self.k.set_voltage(float(volts))

    def do_stop(self, stop: int):
        print(self.rise_time.get())
        if stop == 1:
            self.cycle_rbv.set(0)
            self.cycle.set(0)
            self.status_rbv.set(Status.HOLD)

    def do_start_cycle(self, do: int):
        if do == 1:
            self.cycle_rbv.set(1)

    def do_ramp_on(self, start: bool):
        self.status_rbv.set(Status.RAMP_DOWN)
        seconds = self.rise_time.get()
        to_volts = self.on_setpoint.get()
        step_size = self.step_size.get()
        self.k.voltage_sweep(to_volts, step_size, seconds)

    def do_ramp_off(self, start: bool):
        self.status_rbv.set(Status.RAMP_UP)
        seconds = self.rise_time.get()
        to_volts = self.off_setpoint.get()
        step_size = self.step_size.get()
        self.k.voltage_sweep(to_volts, step_size, seconds)
