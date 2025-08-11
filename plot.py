import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import time

SERIAL_PORT = 'COM5'  
BAUD_RATE = 115200
MAX_DATA_POINTS = 100 

data = deque(maxlen=MAX_DATA_POINTS)

plt.ion()

fig, ax = plt.subplots()
ax.set_title("Real-time Ultrasonic Sensor Data")
ax.set_xlabel("Time (samples)")
ax.set_ylabel("Distance (cm)")
line, = ax.plot([], []) 

ser = None
try:

    print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Connection successful. Reading data...")

    while True:
        try:
            
            serial_line = ser.readline()
            if not serial_line:
                continue

           
            line_str = serial_line.decode('utf-8').strip()
            
            
            parts = line_str.split()
            if len(parts) >= 2 and parts[0] == "Distance:":
                distance_str = parts[1]
                distance = float(distance_str)
            else:
                
                distance = float(line_str)

            
            data.append(distance)

           
            line.set_ydata(data)
            line.set_xdata(range(len(data)))

           
            ax.relim()
            ax.autoscale_view()

            
            fig.canvas.draw()
            fig.canvas.flush_events()
            
        except ValueError:
            print(f"Warning: Could not convert received data to float: '{line_str}'")
        except KeyboardInterrupt:
            print("Stopping plotter...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

except serial.SerialException as e:
    print(f"Error: Could not open serial port {SERIAL_PORT}. {e}")
    print("Please check the port name and make sure the device is connected.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if ser and ser.is_open:
        ser.close()
        print("Serial port closed.")
    print("Exiting.")
