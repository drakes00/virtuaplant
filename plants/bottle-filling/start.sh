#!/bin/sh

echo "VirtuaPlant -- Bottle-filling Factory"
echo "- Starting MODBUS server"
./modbus.py &
echo "- Starting World View"
./world.py &
echo "- Starting HMI"
./hmi.py &
