import cothread

# Import the basic framework components.
from softioc import builder, softioc

from .keithley import Keithley


class Ioc:
    """
    voltageRBV  0 to -500 V	Readback value for the instananeous voltage.
    currentRBV  50 mA	Readback value for the instananeous current.
    voltageOnSetpoint	-500 V	Voltage to use when the detector is in operation. -400 to -600 Vdc (<100mA)
    voltageOffSetpoint	0 V	Voltage to reach during a depolarisation cycle. Probably 0 V.
    depolarisationRiseTime	0.25 s	Time taken to change from voltageOnSetpoint to voltageOffSetpoint
    depolarisationHoldTime	1 s	Time at which the voltage is held at voltageOffSetpoint
    depolarisationFallTime	0.2 s	Time taken to change from voltageOffSetpoint to voltageOnSetpoint
    depolarisationPauseTime	0 s	Time taken after a depolarisation cycle before the detector is declared ready for use.
    depolarisationRepeats	1	Number of times that the depolarisation cycle is repeated
    depolarisationMaxTime	900 s	The maximum time in seconds from the completion of a depolarisation cycle. If this is exceeded, the detector should automatically undergo a depolarisation cycle.
    timeSinceDepolarisationRBV	0-900 s	A counter, counting up the time since the last depolarisation cycle. Refresh at 10 Hz should be fine.
    runDepolarisation	n/a	A value we can send '1' to to initiate a depolarisation cycle.
    statusRBV	0,1,2,3,4	Status of the bias, e.g. 0=voltageOff, 1=voltageOn, 2=rampUp, 3=hold, 4=rampDown.
    healthyStatusRBV	0,1	Value of 1 when the voltage is on, but 0 at all other times.
    stop
    """

    def __init__(self):
        # Set the record prefix
        builder.SetDeviceName("BL15J-EA-HV-01")
        # Create some records
        self.cmd_ramp_off = builder.boolOut(
            "RAMP-OFF", always_update=True, on_update=self.ramp_off
        )
        self.cmd_ramp_on = builder.boolOut(
            "RAMP-ON", always_update=True, on_update=self.ramp_on
        )
        self.cmd_depolarise = builder.boolOut(
            "DEPOLARISE", always_update=True, on_update=self.do_depolarise
        )
        self.cmd_stop = builder.boolOut(
            "STOP", always_update=True, on_update=self.do_stop
        )
        self.cmd_output = builder.boolOut(
            "OUTPUT", always_update=True, on_update=self.do_output
        )
        self.output_rbv = builder.boolIn("OUTPUT_RBV")
        self.voltage_rbv = builder.aIn("VOLTAGE_RBV")
        self.current_rbv = builder.aIn("CURRENT_RBV")
        self.status_rbv = builder.mbbIn(
            "STATUS",
            "VOLTAGE-OFF",
            "VOLTAGE-ON",
            "RAMP-UP",
            "HOLD",
            "RAMP-DOWN",
            ("ERROR", "MAJOR"),
        )
        self.status_rbv = builder.mbbIn(
            "HEALTHY-STATUS", "HEALTHY", ("UNHEALTHY", "MINOR")
        )
        self.on_setpoint = builder.aOut("VOLTAGE-ON-SETPOINT")
        self.off_setpoint = builder.aOut("VOLTAGE-OFF-SETPOINT")
        self.rise_time = builder.aOut("RISE-TIME")
        self.hold_time = builder.aOut("HOLD-TIME")
        self.fall_time = builder.aOut("FALL-TIME")
        self.depolarise_repeats = builder.longOut("DEPOLARISE-REPEATS")
        self.depolarise_pause_time = builder.longOut("DEPOLARISE-PAUSE-TIME")

        # Boilerplate get the IOC started
        builder.LoadDatabase()
        softioc.iocInit()

        self.k = Keithley()

        cothread.Spawn(self.update)
        # Finally leave the IOC running with an interactive shell.
        softioc.interactive_ioc(globals())

    # Start processes required to be run after iocInit
    def update(self):
        while True:
            self.voltage_rbv.set(self.k.get_voltage())
            self.current_rbv.set(self.k.get_current())
            self.output_rbv.set(self.k.get_source_status())
            cothread.Sleep(1)

    def do_output(self, on_off: bool):
        if on_off:
            self.k.source_on()
        else:
            self.k.source_off()

    def do_stop(self):
        pass

    def do_depolarise(self):
        pass

    def ramp_on(self, start: bool):
        self.k.source_voltage_ramp(start=0, stop=50, steps=50, seconds=20)

    def ramp_off(self, start: bool):
        self.k.source_voltage_ramp(start=0, stop=50, steps=50, seconds=20)
