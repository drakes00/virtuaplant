#!/usr/bin/env python

#########################################
# Imports
#########################################
# - Modbus protocol
import asyncio
import sys
from pymodbus.client import ModbusTcpClient
from pymodbus.server import ModbusTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock
from pymodbus.exceptions import ConnectionException


#########################################
# PLC
#########################################
PLC_SERVER_IP   = "127.0.0.1"
PLC_SERVER_PORT = 5020

PLC_RW_ADDR = 0x0
PLC_TAG_RUN = 0x0

PLC_RO_ADDR	= 0x3E8
PLC_TAG_LEVEL   = 0x1
PLC_TAG_CONTACT = 0x2
PLC_TAG_MOTOR   = 0x3
PLC_TAG_NOZZLE  = 0x4

#########################################
# MOTOR actuator
#########################################
MOTOR_SERVER_IP     = "127.0.0.1"
MOTOR_SERVER_PORT   = 5021

MOTOR_RW_ADDR = 0x0
MOTOR_TAG_RUN = 0x0

#########################################
# NOZZLE actuator
#########################################
NOZZLE_SERVER_IP    = "127.0.0.1"
NOZZLE_SERVER_PORT  = 5022

NOZZLE_RW_ADDR = 0x0
NOZZLE_TAG_RUN = 0x0

#########################################
# LEVEL sensor
#########################################
LEVEL_SERVER_IP     = "127.0.0.1"
LEVEL_SERVER_PORT   = 5023

LEVEL_RO_ADDR = 0x0
LEVEL_TAG_SENSOR = 0x0

#########################################
# CONTACT sensor
#########################################
CONTACT_SERVER_IP   = "127.0.0.1"
CONTACT_SERVER_PORT = 5024

CONTACT_RO_ADDR = 0x0
CONTACT_TAG_SENSOR = 0x0

class ClientModbus:
    def __init__(self, address, port):
        self._client = ModbusTcpClient(address, port=port, framer="socket")
        self._client.connect()
        assert self._client.connected
    
    def read(self, addr):
        regs = self.readln(addr, 1)
        return regs[0]
    
    def readln(self, addr, size):
        rr = self._client.read_holding_registers(addr, count=size, slave=1)
        if not rr or not rr.registers:
            raise ConnectionException("Failed to read registers")
        regs = rr.registers
        if not regs or len(regs) < size:
            raise ConnectionException("Insufficient data received")
        return regs
    
    def write(self, addr, data):
        self._client.write_register(addr, data)
    
    def writeln(self, addr, data, size):
        self._client.write_registers(addr, data)


class ServerModbus:
    def __init__(self, address, port):
        block = ModbusSequentialDataBlock(0x00, [0]*0x3FF)
        store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
        self.context = ModbusServerContext(slaves=store, single=True)

        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = 'MockPLCs'
        self.identity.ProductCode = 'MP'
        self.identity.VendorUrl = 'http://github.com/bashwork/pymodbus/'
        self.identity.ProductName = 'MockPLC 3000'
        self.identity.ModelName = 'MockPLC Ultimate'
        self.identity.MajorMinorRevision = '1.0'

        self.address = address
        self.port = port

    async def start(self):
        print(f"Starting Modbus server on {self.address}:{self.port}...")
        await ModbusTcpServer(
            context=self.context,
            identity=self.identity,
            address=(self.address, self.port)
        ).serve_forever(background=True)

async def main():
    # Initialize all servers
    motor = ServerModbus(MOTOR_SERVER_IP, port=MOTOR_SERVER_PORT)
    nozzle = ServerModbus(NOZZLE_SERVER_IP, port=NOZZLE_SERVER_PORT)
    level = ServerModbus(LEVEL_SERVER_IP, port=LEVEL_SERVER_PORT)
    contact = ServerModbus(CONTACT_SERVER_IP, port=CONTACT_SERVER_PORT)
    plc = ServerModbus(PLC_SERVER_IP, port=PLC_SERVER_PORT)

    # Start all servers concurrently
    await motor.start()
    await nozzle.start()
    await level.start()
    await contact.start()
    await plc.start()

    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
