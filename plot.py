import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import time

# --- Configuration ---
# On Linux, if you get a "Permission denied" error, you may need to add your user
# to the 'dialout' group by running this command in your terminal:
#   sudo usermod -a -G dialout $USER
# After running the command, you must log out and log back in for the change to take effect.
SERIAL_PORT = '/dev/ttyUSB0'  # Change this to your Arduino/ESP32 port
BAUD_RATE = 115200
MAX_DATA_POINTS = 100  # Number of data points to display on the plot

# --- Setup ---
# Initialize deque to store data with a maximum length
data = deque(maxlen=MAX_DATA_POINTS)

# Enable interactive mode for matplotlib
plt.ion()

# Create a figure and axis for the plot
fig, ax = plt.subplots()
ax.set_title("Real-time Ultrasonic Sensor Data")
ax.set_xlabel("Time (samples)")
ax.set_ylabel("Distance (cm)")
line, = ax.plot([], []) # Create an empty line object

# --- Main Loop ---
ser = None
try:
    # Establish serial connection
    print(f"Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Wait for the connection to establish
    print("Connection successful. Reading data...")

    while True:
        try:
            # Read a line from the serial port
            serial_line = ser.readline()
            if not serial_line:
                continue

            # Decode bytes to string and convert to float
            # Assumes the Arduino sends a number followed by a newline, e.g., "15.4\n"
            distance = float(serial_line.decode('utf-8').strip())
            
            # Append the new data point
            data.append(distance)

            # --- Update Plot ---
            # Set the data for the line object
            line.set_ydata(data)
            line.set_xdata(range(len(data)))

            # Re-scale the axes
            ax.relim()
            ax.autoscale_view()

            # Redraw the canvas
            fig.canvas.draw()
            fig.canvas.flush_events()
            
        except ValueError:
            # Handle cases where the data is not a valid number
            print(f"Warning: Could not convert received data to float: '{serial_line.strip()}'")
        except KeyboardInterrupt:
            # Allow clean exit with Ctrl+C
            print("Stopping plotter...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

except serial.SerialException as e:
    print(f"Error: Could not open serial port {SERIAL_PORT}. {e}")
    print("Please check the port name and make sure the device is connected.")
    print("Available ports:")
    ports = serial.tools.list_ports.comports()
    if ports:
        for port in ports:
            print(f"  {port.device}: {port.description}")
    else:
        print("  No serial ports found.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if ser and ser.is_open:
        ser.close()
        print("Serial port closed.")
    print("Exiting.")
