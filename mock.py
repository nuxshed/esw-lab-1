import serial
import time
import random
import sys

# --- Configuration ---
MOCK_PORT_NAME = "/dev/pts/2" # CHANGE THIS if your port is different

BAUD_RATE = 9600

def run_mock_sender():
    """
    Opens the virtual serial port and sends simulated sensor data periodically.
    """
    print(f"Attempting to open mock serial port: {MOCK_PORT_NAME}")

    try:
        mock_serial_port = serial.Serial(MOCK_PORT_NAME, BAUD_RATE)
    except serial.SerialException as e:
        print(f"Error: Could not open port '{MOCK_PORT_NAME}'.")
        print(f"  - Is socat running?")
        print(f"  - Did you use the correct port name from the socat output?")
        print(f"  - Original error: {e}")
        sys.exit(1)

    print(f"Successfully opened {MOCK_PORT_NAME}. Sending mock data...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            temperature = 20 + random.random() * 5
            humidity = 50 + random.random() * 10
            
            data_string = f"Temperature: {temperature:.2f} C, Humidity: {humidity:.2f} %\n"
            
            mock_serial_port.write(data_string.encode('utf-8'))
            
            print(f"Sent: {data_string.strip()}")
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping mock data sender.")
    finally:
        if mock_serial_port.is_open:
            mock_serial_port.close()
            print(f"Closed port {MOCK_PORT_NAME}.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        MOCK_PORT_NAME = sys.argv[1]
    run_mock_sender()
