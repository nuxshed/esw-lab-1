import sys
import re
import serial
import serial.tools.list_ports
import statistics
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QComboBox, QLineEdit, QTextEdit,
                             QLabel, QMessageBox, QGroupBox, QFormLayout, QSplitter)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt
from PyQt6.QtCharts import QChart, QChartView, QSplineSeries, QValueAxis
from PyQt6.QtGui import QPainter, QFont

class SerialWorker(QObject):
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
        self._is_running = False


class SerialMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Serial Monitor with Real-Time Chart")
        self.setGeometry(100, 100, 1000, 700) 

        self.serial_thread = None
        self.serial_worker = None
        self.is_connected = False
        self.data_point_counter = 0

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)

        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)

        self.chart = QChart()
        self.chart.setTitle("Real-Time Distance Measurement")
        self.series = QSplineSeries()
        self.chart.addSeries(self.series)
        self.axis_x = QValueAxis()
        self.axis_y = QValueAxis()
        self.axis_x.setLabelFormat("%i")
        self.axis_x.setTitleText("Time (samples)")
        self.axis_y.setTitleText("Distance (units)")
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.chart_view)
        self.splitter.addWidget(self.data_display)
        self.splitter.setSizes([400, 200])
        self.left_layout.addWidget(self.splitter)

        self.right_panel = QWidget()
        self.right_panel.setFixedWidth(280)
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.connection_group = QGroupBox("Connection Settings")
        self.connection_layout = QFormLayout()
        
        self.port_combo = QComboBox()
        self.connection_layout.addRow("COM Port:", self.port_combo)
        
        self.baud_input = QLineEdit("115200")
        self.connection_layout.addRow("Baud Rate:", self.baud_input)

        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.populate_ports)
        self.connection_layout.addRow(self.refresh_button)

        self.manual_port_input = QLineEdit()
        self.manual_port_input.setPlaceholderText("e.g., /dev/ttyACM0")
        self.add_port_button = QPushButton("Add")
        self.add_port_button.clicked.connect(self.add_manual_port)
        manual_port_layout = QHBoxLayout()
        manual_port_layout.addWidget(self.manual_port_input)
        manual_port_layout.addWidget(self.add_port_button)
        self.connection_layout.addRow("Manual Port:", manual_port_layout)
        
        self.connection_group.setLayout(self.connection_layout)

        self.controls_group = QGroupBox("Controls")
        self.controls_layout = QVBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_graph_and_log)
        self.clear_button.setEnabled(False)
        self.controls_layout.addWidget(self.connect_button)
        self.controls_layout.addWidget(self.clear_button)
        self.controls_group.setLayout(self.controls_layout)

        self.stats_group = QGroupBox("Statistics")
        self.stats_layout = QFormLayout()
        self.avg_label = QLabel("N/A")
        self.min_label = QLabel("N/A")
        self.max_label = QLabel("N/A")
        self.stdev_label = QLabel("N/A")
        self.stats_layout.addRow("Average:", self.avg_label)
        self.stats_layout.addRow("Minimum:", self.min_label)
        self.stats_layout.addRow("Maximum:", self.max_label)
        self.stats_layout.addRow("Std Dev:", self.stdev_label)
        self.stats_group.setLayout(self.stats_layout)

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setWordWrap(True)

        self.right_layout.addWidget(self.connection_group)
        self.right_layout.addWidget(self.controls_group)
        self.right_layout.addWidget(self.stats_group)
        self.right_layout.addWidget(self.status_label)
        self.right_layout.addStretch()

        self.main_layout.addWidget(self.left_panel, 1) 
        self.main_layout.addWidget(self.right_panel, 0)

        self.populate_ports()

    def populate_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.port_combo.addItem("No ports found")
        else:
            for port in sorted(ports):
                self.port_combo.addItem(f"{port.device}: {port.description}", userData=port)

    def add_manual_port(self):
        port_name = self.manual_port_input.text().strip()
        if not port_name:
            QMessageBox.warning(self, "Input Error", "Manual port name cannot be empty.")
            return
        
        class MockPortInfo:
            def __init__(self, device):
                self.device = device; self.description = "Manually Added"
        
        mock_port = MockPortInfo(port_name)
        self.port_combo.addItem(f"{mock_port.device}: {mock_port.description}", userData=mock_port)
        self.port_combo.setCurrentIndex(self.port_combo.count() - 1)
        self.manual_port_input.clear()

    def toggle_connection(self):
        if not self.is_connected:
            current_index = self.port_combo.currentIndex()
            if current_index == -1 or "No ports found" in self.port_combo.currentText():
                QMessageBox.warning(self, "Connection Error", "No serial port selected.")
                return
            port_info = self.port_combo.itemData(current_index)
            port_device = port_info.device
            try:
                baud_rate = int(self.baud_input.text())
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter a valid integer baud rate.")
                return
            self.start_serial_thread(port_device, baud_rate)
        else:
            self.stop_serial_thread()

    def start_serial_thread(self, port, baud_rate):
        self.clear_graph_and_log()
        self.axis_y.setRange(0, 50)
        
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
        self.status_label.setText(f"Status: Connected to {port} @ {baud_rate} baud")
        self.clear_button.setEnabled(True)
        self.connection_group.setEnabled(False)

    def stop_serial_thread(self):
        if self.serial_worker:
            self.serial_worker.stop()
        
        self.is_connected = False
        self.connect_button.setText("Connect")
        self.status_label.setText("Status: Disconnected")
        self.clear_button.setEnabled(False)
        self.connection_group.setEnabled(True)

    def append_data(self, data):
        self.data_display.append(data)
        
        match = re.search(r'^Distance:\s*(\d*\.?\d+)', data)
        if match:
            try:
                value = float(match.group(1))
                self.series.append(self.data_point_counter, value)
                if self.series.count() > 50:
                    self.series.remove(0)
                    self.axis_x.setRange(self.data_point_counter - 49, self.data_point_counter)
                
                current_min_y = self.axis_y.min()
                current_max_y = self.axis_y.max()
                if value > current_max_y: self.axis_y.setMax(value + 1)
                if value < current_min_y: self.axis_y.setMin(value - 1)

                self.data_point_counter += 1
                self.update_statistics()
            except (ValueError, IndexError): pass

    def clear_graph_and_log(self):
        self.series.clear()
        self.data_display.clear()
        self.data_point_counter = 0
        self.axis_x.setRange(0, 50)
        self.reset_stats_labels()

    def reset_stats_labels(self):
        self.avg_label.setText("N/A")
        self.min_label.setText("N/A")
        self.max_label.setText("N/A")
        self.stdev_label.setText("N/A")

    def update_statistics(self):
        points = self.series.points()
        if not points:
            self.reset_stats_labels()
            return

        y_values = [p.y() for p in points]
        
        min_val = min(y_values)
        max_val = max(y_values)
        avg_val = statistics.mean(y_values)
        
        if len(y_values) > 1:
            stdev_val = statistics.stdev(y_values)
        else:
            stdev_val = 0

        self.min_label.setText(f"{min_val:.2f}")
        self.max_label.setText(f"{max_val:.2f}")
        self.avg_label.setText(f"{avg_val:.2f}")
        self.stdev_label.setText(f"{stdev_val:.2f}")
        
    def on_serial_error(self, error_message):
        QMessageBox.critical(self, "Serial Port Error", error_message)
        self.stop_serial_thread()

    def closeEvent(self, event):
        self.stop_serial_thread()
        event.accept()


STYLESHEET = """
QWidget {
    background-color: #2e3440;
    color: #d8dee9;
    font-family: Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow {
    background-color: #2e3440;
}
QGroupBox {
    background-color: #3b4252;
    border: 1px solid #4c566a;
    border-radius: 5px;
    margin-top: 1ex;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 3px;
}
QLabel {
    color: #eceff4;
}
QLineEdit, QComboBox, QTextEdit {
    background-color: #434c5e;
    border: 1px solid #4c566a;
    border-radius: 4px;
    padding: 5px;
    color: #d8dee9;
}
QTextEdit {
    font-family: Monospace;
}
QPushButton {
    background-color: #5e81ac;
    color: #eceff4;
    border: none;
    border-radius: 4px;
    padding: 8px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #81a1c1;
}
QPushButton:pressed {
    background-color: #88c0d0;
}
QPushButton:disabled {
    background-color: #4c566a;
    color: #d8dee9;
}
QComboBox::drop-down {
    border: none;
}
QMessageBox {
    background-color: #3b4252;
}
QChart {
    background-color: transparent;
}
"""

if __name__ == "__main__":
    try:
        from PyQt6.QtCharts import QChart
    except ImportError:
        print("Error: PyQt6-Charts is not installed.")
        print("Please install it by running: pip install PyQt6-Charts")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    main_window = SerialMonitorApp()
    main_window.show()
    sys.exit(app.exec())