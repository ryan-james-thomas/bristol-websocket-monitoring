#!/usr/bin/python3

import asyncio
import websockets
import serial
import json
import Bristol621

"""
Define the Bristol621 device.  The serial device given here maps to a specific USB port on the
Raspberry Pi - in this case, the bottom-right USB port
"""
device = Bristol621.Wavemeter('/dev/serial/by-path/platform-3f980000.usb-usb-0:1.2:1.0-port0')
device.set_wavelength_units('GHz')
device.set_medium('vacuum') 

"""
Define a measurement/control class.  This just makes it easier to pass a bunch
of parameters from one asynchronous function to the next
"""
class MeasurementResult:
    def __init__(self,frequency=0,power=0,dt=0):
        self.frequency = frequency
        self.power = power
        self.dt = 0
        self.err = False
        self.msg = "No Error"

    def serialize(self):
        v = {"frequency":f"{self.frequency:.6f}",
             "power":f"{self.power:.3f}",
             "err":self.err,
             "msg":self.msg}
        return json.dumps(v)

"""
Instantiate a MeasurementResult object in the global scope so that it can be read and written to
by all subsequent functions
"""
meas = MeasurementResult(0,0,0.1)

"""
Define an asynchronous function that gets data from the wavemeter.  We use a try/catch statement
to catch when serial transactions fail which correspond to the wavemeter either not being
connected or not being connected to the correct port.  If a serial exception occurs, then we
increase the measurement update time dt from 0.1 s to 2 s since nothing of interest is happening.
"""
async def get_wavemeter_data():
    try:
        """
        This if statement attempts to open the serial port if it is not open and will raise a
        serial exception if it fails
        """
        if not device.con.is_open:
            device.con.open()
        meas.frequency = device.get_wavelength()
        meas.power = device.get_power()
        meas.err = False
        meas.msg = "No Error"
        meas.dt = 0.1

    except serial.SerialException:
        device.con.close()
        meas.dt = 2
        meas.err = True
        meas.msg = "Error communicating with device"

#    print(f'Frequency: {meas.frequency:.6f}, Power: {meas.power:.3f}')
    return meas.err


"""
This is just a continuous loop that attempts to read data from the wavemeter and then waits for
meas.dt seconds
"""
async def serial_handler():
    while True:
        await get_wavemeter_data()
        await asyncio.sleep(meas.dt)

"""
This function sends measurement data to clients via the Websocket protocol
"""
async def producer_handler(websocket, path):
    while True:
        # message = await get_serial_data()
        await websocket.send(meas.serialize())
        await asyncio.sleep(meas.dt)

"""
This creates a Websocket server associated with the IP address in quotes and the port (last arguments)
"""
start_server = websockets.serve(producer_handler,"172.22.251.154",5678)

"""
The asyncio.gather() function allows one to wait for both the specified objects (serial_handler() and start_server)
to return indepedently.  This means that the serial handler runs indepdently of the server, so the wavemeter is polled
for data indepdent of whatever is happening with the Websocket server.  The server just sends the last data returned to
the clients.
"""
async def main():
    await asyncio.gather(serial_handler(),start_server)


asyncio.get_event_loop().run_until_complete(main())
asyncio.get_event_loop().run_forever()
