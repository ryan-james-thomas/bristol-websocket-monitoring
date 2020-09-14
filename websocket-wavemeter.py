#!/usr/bin/python3

import asyncio
import random
import websockets
import serial
import math
import json
import Bristol621
import struct

device = Bristol621.Wavemeter('/dev/serial/by-path/platform-3f980000.usb-usb-0:1.2:1.0-port0')
device.set_wavelength_units('GHz')
device.set_medium('vacuum')

class ProcessControl:
    def __init__(self,dt = 0.1):
        self.dt = dt
        

class MeasurementResult:
    def __init__(self,frequency,power):
        self.frequency = 0
        self.power = 0
        self.err = False
        self.msg = "No Error"

    def serialize(self):
        v = {"frequency":f"{self.frequency:.6f}",
             "power":f"{self.power:.3f}",
             "err":self.err,
             "msg":self.msg}
        return json.dumps(v)

cntrl = ProcessControl(0.1)
meas = MeasurementResult(0,0)

async def get_wavemeter_data():
    try:
        if not device.con.is_open:
            device.con.open()
        meas.frequency = device.get_wavelength()
        meas.power = device.get_power()
        meas.err = False
        meas.msg = "No Error"
        cntrl.dt = 0.1

    except serial.SerialException:
        device.con.close()
        cntrl.dt = 2
        meas.err = True
        meas.msg = "Error communicating with device"


    except struct.error:
        meas.err = True
        meas.msg = "Error getting data"


    except TypeError:
        meas.err = True
        meas.msg = "Error getting data"


#    print(f'Frequency: {meas.frequency:.6f}, Power: {meas.power:.3f}')
    return meas.err



async def serial_handler():
    while True:
        await get_wavemeter_data()
        await asyncio.sleep(cntrl.dt)

async def producer_handler(websocket, path):
    while True:
        # message = await get_serial_data()
        await websocket.send(meas.serialize())
        await asyncio.sleep(cntrl.dt)

start_server = websockets.serve(producer_handler,"172.22.251.154",5678)

async def main():
    await asyncio.gather(serial_handler(),start_server)


asyncio.get_event_loop().run_until_complete(main())
asyncio.get_event_loop().run_forever()
