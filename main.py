import sys
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QComboBox, QLineEdit, QTextEdit,
                             QLabel, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class SerialWorker(QObject):
    """
    Worker thread for reading from the serial port.
    Emits a signal with the data received.
    """
    data_received = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None
        self._is_running = True

    def run(self):
        """
        Connects to the serial port and reads data continuously.
        """
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=1)
        except serial.SerialException as e:
            self.error.emit(f"Error opening port: {e}")
            self.finished.emit()
            return

        while self._is_running and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        self.data_received.emit(line)
            except serial.SerialException as e:
                self.error.emit(f"Serial error: {e}")
                self._is_running = False
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.finished.emit()

    def stop(self):
        """
        Stops the reading loop and closes the serial port.
        """
        self._is_running = False


class SerialMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Serial Monitor")
        self.setGeometry(100, 100, 600, 450)

        self.serial_thread = None
        self.serial_worker = None
        self.is_connected = False
        self.port_list = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        config_layout = QHBoxLayout()
        
        self.port_label = QLabel("COM Port:")
        self.port_combo = QComboBox()
        config_layout.addWidget(self.port_label)
        config_layout.addWidget(self.port_combo)

        self.baud_label = QLabel("Baud Rate:")
        self.baud_input = QLineEdit("9600")
        config_layout.addWidget(self.baud_label)
        config_layout.addWidget(self.baud_input)
        
        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.populate_ports)
        config_layout.addWidget(self.refresh_button)
        
        self.layout.addLayout(config_layout)

        manual_add_layout = QHBoxLayout()
        self.manual_port_input = QLineEdit()
        self.manual_port_input.setPlaceholderText("e.g., /dev/pts/3")
        self.add_port_button = QPushButton("Add Manual Port")
        self.add_port_button.clicked.connect(self.add_manual_port)
        manual_add_layout.addWidget(QLabel("Manual Port:"))
        manual_add_layout.addWidget(self.manual_port_input)
        manual_add_layout.addWidget(self.add_port_button)
        self.layout.addLayout(manual_add_layout)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        self.layout.addWidget(self.connect_button)
        
        self.status_label = QLabel("Status: Disconnected")
        self.layout.addWidget(self.status_label)

        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.layout.addWidget(self.data_display)

        self.populate_ports()

    def populate_ports(self):
        """
        Scans for available serial ports and adds them to the dropdown.
        """
        self.port_combo.clear()
        self.port_list = serial.tools.list_ports.comports()
        
        if not self.port_list:
            self.port_combo.addItem("No ports found")
        else:
            for port in sorted(self.port_list):
                description = f"{port.device}: {port.description}"
                self.port_combo.addItem(description, userData=port)

    def add_manual_port(self):
        """
        Adds a port from the manual input field to the dropdown list.
        """
        port_name = self.manual_port_input.text().strip()
        if not port_name:
            QMessageBox.warning(self, "Input Error", "Manual port name cannot be empty.")
            return

        class MockPortInfo:
            def __init__(self, device):
                self.device = device
                self.description = "Manually Added Port"

        mock_port = MockPortInfo(port_name)
        self.port_list.append(mock_port)
        
        description = f"{mock_port.device}: {mock_port.description}"
        self.port_combo.addItem(description, userData=mock_port)
        self.port_combo.setCurrentIndex(self.port_combo.count() - 1)
        self.manual_port_input.clear()


    def toggle_connection(self):
        """
        Handles the logic for connecting to and disconnecting from the serial port.
        """
        if not self.is_connected:
            current_index = self.port_combo.currentIndex()
            if current_index == -1 or "No ports found" in self.port_combo.currentText():
                QMessageBox.warning(self, "Connection Error", "No serial port selected.")
                return

            port_info = self.port_combo.itemData(current_index)
            if not port_info:
                 port_device = self.port_combo.currentText()
            else:
                 port_device = port_info.device
            
            baud_rate_text = self.baud_input.text()

            try:
                baud_rate = int(baud_rate_text)
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter a valid integer for the baud rate.")
                return

            self.start_serial_thread(port_device, baud_rate)
        else:
            self.stop_serial_thread()

    def start_serial_thread(self, port, baud_rate):
        self.serial_worker = SerialWorker(port, baud_rate)
        self.serial_thread = QThread()
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.run)
        self.serial_worker.finished.connect(self.serial_thread.quit)
        self.serial_worker.finished.connect(self.serial_worker.deleteLater)
        self.serial_thread.finished.connect(self.serial_thread.deleteLater)
        self.serial_worker.data_received.connect(self.append_data)
        self.serial_worker.error.connect(self.on_serial_error)
        self.serial_thread.start()
        
        self.is_connected = True
        self.connect_button.setText("Disconnect")
        self.status_label.setText(f"Status: Connected to {port} at {baud_rate} baud")
        self.port_combo.setEnabled(False)
        self.baud_input.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.manual_port_input.setEnabled(False)
        self.add_port_button.setEnabled(False)


    def stop_serial_thread(self):
        if self.serial_worker:
            self.serial_worker.stop()
        
        self.is_connected = False
        self.connect_button.setText("Connect")
        self.status_label.setText("Status: Disconnected")
        self.port_combo.setEnabled(True)
        self.baud_input.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.manual_port_input.setEnabled(True)
        self.add_port_button.setEnabled(True)


    def append_data(self, data):
        self.data_display.append(data)

    def on_serial_error(self, error_message):
        QMessageBox.critical(self, "Serial Port Error", error_message)
        self.stop_serial_thread()

    def closeEvent(self, event):
        self.stop_serial_thread()
        event.accept()


if __name__ == "__main__":
    try:
        from PyQt6.QtWidgets import QApplication
        import serial
    except ImportError as e:
        print(f"Error: A required library is missing: {e.name}")
        print("Please install the necessary packages by running:")
        print("pip install pyserial pyqt6")
        sys.exit(1)

    app = QApplication(sys.argv)
    main_window = SerialMonitorApp()
    main_window.show()
    sys.exit(app.exec())
