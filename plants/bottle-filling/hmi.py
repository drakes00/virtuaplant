#!/usr/bin/env python

import sys
from gi.repository import GLib, Gtk, GObject
from modbus import ClientModbus as Client
from modbus import ConnectionException
from world import *


class HMIWindow(Gtk.Window):
    def resetLabels(self):
        self.bottlePositionValue.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.motorStatusValue.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.levelHitValue.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.processStatusValue.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.nozzleStatusValue.set_markup("<span weight='bold' foreground='gray33'>N/A</span>")
        self.connectionStatusValue.set_markup("<span weight='bold' foreground='red'>OFFLINE</span>")

    def __init__(self, address, port):
        super().__init__(title="Bottle-filling factory - HMI - VirtuaPlant")

        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)

        self.client = Client(address, port=port)

        elementIndex = 0

        # Grid
        grid = Gtk.Grid()
        grid.set_row_spacing(15)
        grid.set_column_spacing(10)
        self.set_child(grid)

        # Main title label
        label = Gtk.Label()
        label.set_markup("<span weight='bold' size='x-large'>Bottle-filling process status</span>")
        grid.attach(label, 0, elementIndex, 2, 1)
        elementIndex += 1

        # Bottle in position label
        bottlePositionLabel = Gtk.Label(label="Bottle in position")
        bottlePositionValue = Gtk.Label()
        grid.attach(bottlePositionLabel, 0, elementIndex, 1, 1)
        grid.attach(bottlePositionValue, 1, elementIndex, 1, 1)
        elementIndex += 1

        # Nozzle status label
        nozzleStatusLabel = Gtk.Label(label="Nozzle Status")
        nozzleStatusValue = Gtk.Label()
        grid.attach(nozzleStatusLabel, 0, elementIndex, 1, 1)
        grid.attach(nozzleStatusValue, 1, elementIndex, 1, 1)
        elementIndex += 1

        # Motor status label
        motorStatusLabel = Gtk.Label(label="Motor Status")
        motorStatusValue = Gtk.Label()
        grid.attach(motorStatusLabel, 0, elementIndex, 1, 1)
        grid.attach(motorStatusValue, 1, elementIndex, 1, 1)
        elementIndex += 1

        # Level hit label
        levelHitLabel = Gtk.Label(label="Level Hit")
        levelHitValue = Gtk.Label()
        grid.attach(levelHitLabel, 0, elementIndex, 1, 1)
        grid.attach(levelHitValue, 1, elementIndex, 1, 1)
        elementIndex += 1

        # Process status
        processStatusLabel = Gtk.Label(label="Process Status")
        processStatusValue = Gtk.Label()
        grid.attach(processStatusLabel, 0, elementIndex, 1, 1)
        grid.attach(processStatusValue, 1, elementIndex, 1, 1)
        elementIndex += 1

        # Connection status
        connectionStatusLabel = Gtk.Label(label="Connection Status")
        connectionStatusValue = Gtk.Label()
        grid.attach(connectionStatusLabel, 0, elementIndex, 1, 1)
        grid.attach(connectionStatusValue, 1, elementIndex, 1, 1)
        elementIndex += 1

        # Run and Stop buttons
        runButton = Gtk.Button(label="Run")
        stopButton = Gtk.Button(label="Stop")

        runButton.connect("clicked", self.setProcess, 1)
        stopButton.connect("clicked", self.setProcess, 0)

        grid.attach(runButton, 0, elementIndex, 1, 1)
        grid.attach(stopButton, 1, elementIndex, 1, 1)
        elementIndex += 1

        # NEW: Nozzle Control Buttons
        openNozzleButton = Gtk.Button(label="Open Nozzle")
        closeNozzleButton = Gtk.Button(label="Close Nozzle")

        openNozzleButton.connect("clicked", self.controlNozzle, 1)
        closeNozzleButton.connect("clicked", self.controlNozzle, 0)

        grid.attach(openNozzleButton, 0, elementIndex, 1, 1)
        grid.attach(closeNozzleButton, 1, elementIndex, 1, 1)
        elementIndex += 1

        # NEW: Conveyor Motor Control Buttons
        startMotorButton = Gtk.Button(label="Start Conveyor")
        stopMotorButton = Gtk.Button(label="Stop Conveyor")

        startMotorButton.connect("clicked", self.controlMotor, 1)
        stopMotorButton.connect("clicked", self.controlMotor, 0)

        grid.attach(startMotorButton, 0, elementIndex, 1, 1)
        grid.attach(stopMotorButton, 1, elementIndex, 1, 1)
        elementIndex += 1

        # VirtuaPlant branding
        virtuaPlant = Gtk.Label()
        virtuaPlant.set_markup("<span size='small'>VirtuaPlant - HMI</span>")
        grid.attach(virtuaPlant, 0, elementIndex, 2, 1)

        # Attach Value Labels
        self.processStatusValue = processStatusValue
        self.connectionStatusValue = connectionStatusValue
        self.levelHitValue = levelHitValue
        self.motorStatusValue = motorStatusValue
        self.bottlePositionValue = bottlePositionValue
        self.nozzleStatusValue = nozzleStatusValue

        self.resetLabels()
        GLib.timeout_add_seconds(1, self.update_status)

    def setProcess(self, widget, data=None):
        try:
            self.client.write(PLC_RW_ADDR + PLC_TAG_RUN, data)
        except:
            pass

    def controlNozzle(self, widget, state):
        """Opens (1) or Closes (0) the nozzle manually"""
        try:
            self.client.write(PLC_RW_ADDR + PLC_TAG_NOZZLE, state)
        except:
            pass

    def controlMotor(self, widget, state):
        """Starts (1) or Stops (0) the conveyor belt manually"""
        try:
            self.client.write(PLC_RW_ADDR + PLC_TAG_MOTOR, state)
        except:
            pass

    def update_status(self):
        try:
            regs = self.client.readln(PLC_RO_ADDR, 17)

            if regs[PLC_TAG_CONTACT] == 1:
                self.bottlePositionValue.set_markup("<span weight='bold' foreground='green'>YES</span>")
            else:
                self.bottlePositionValue.set_markup("<span weight='bold' foreground='red'>NO</span>")

            if regs[PLC_TAG_LEVEL] == 1:
                self.levelHitValue.set_markup("<span weight='bold' foreground='green'>YES</span>")
            else:
                self.levelHitValue.set_markup("<span weight='bold' foreground='red'>NO</span>")

            if regs[PLC_TAG_MOTOR] == 1:
                self.motorStatusValue.set_markup("<span weight='bold' foreground='green'>ON</span>")
            else:
                self.motorStatusValue.set_markup("<span weight='bold' foreground='red'>OFF</span>")

            if regs[PLC_TAG_NOZZLE] == 1:
                self.nozzleStatusValue.set_markup("<span weight='bold' foreground='green'>OPEN</span>")
            else:
                self.nozzleStatusValue.set_markup("<span weight='bold' foreground='red'>CLOSED</span>")

            regs = self.client.readln(PLC_RW_ADDR, 17)

            if regs[PLC_TAG_RUN] == 1:
                self.processStatusValue.set_markup("<span weight='bold' foreground='green'>RUNNING</span>")
            else:
                self.processStatusValue.set_markup("<span weight='bold' foreground='red'>STOPPED</span>")

            self.connectionStatusValue.set_markup("<span weight='bold' foreground='green'>ONLINE</span>")

        except ConnectionException:
            if not self.client.connect():
                self.resetLabels()
        except:
            raise
        finally:
            return True


def main():
    app = Gtk.Application(application_id='org.virtuaplant.bottlefilling')

    def on_activate(app):
        win = HMIWindow(PLC_SERVER_IP, PLC_SERVER_PORT)
        win.set_application(app)
        win.present()

    app.connect('activate', on_activate)
    return app.run(None)


if __name__ == "__main__":
    sys.exit(main())
