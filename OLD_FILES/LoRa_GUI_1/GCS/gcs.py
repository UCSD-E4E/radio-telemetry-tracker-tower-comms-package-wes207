import sys, serial, threading, time, os
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QCheckBox, QPushButton, QDialog,
    QGroupBox, QComboBox, QHBoxLayout, QGridLayout, QScrollArea, QTextEdit,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QDate, QTime
from PyQt5.QtGui import QTextCursor, QFont, QColor, QPalette

# Serial communication parameters
auto = False
port = 'COM17'  
port = '/dev/tty.usbserial-0001'
baudrate = 115200  # Serial communication speed

# Global variables
serial_connection = None  
receive_thread = None     
send_thread = None        
thr_running = False       # Flag to indicate if threads are running
serial_port = None       

tower = 1                 # Default tower number
rotation_mode = False     # Enable or disable rotating through multiple towers
tower_curr = 1            # Current tower in rotation
max_tower = 4             # Maximum number of towers

cmd = "idn?"              # Default command to be sent
dly_cmd = 200             # Delay for commands in ms
dly_comm = 2000           # Delay for communications in ms

rssi = 0                  # Placeholder for signal strength
station = "-"             # Station ID placeholder
idn = "-"                 # Device ID placeholder
sync_flg = True           # Synchronization flag
filename = "GCS_data.csv" # File to save received data
Sequence_script = "Sequence_Script_1.txt"  # Script file for sequence operations

# Utility function to read an entire file as a string
def load_string_from_file(filepath):
    """
    Loads the entire content of a text file into a single string.
    Returns an empty string if the file does not exist or an error occurs.
    """
    try:
        with open(filepath, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return ""
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return ""

# Check if a string can be interpreted as a number
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# Save a line of text to a file (append or overwrite)
def save_string_line(filename, line, append=True):
    # Validate input types
    if not isinstance(filename, str):
        raise TypeError(f"filename must be a string, not {type(filename).__name__}")
    if not isinstance(line, str):
        raise TypeError(f"line must be a string, not {type(line).__name__}")
    if not isinstance(append, bool):
        raise TypeError(f"append must be a bool, not {type(append).__name__}")

    # Determine mode: 'a' = append, 'w' = write new
    mode = "a" if append else "w"
    try:
        with open(filename, mode) as file:
            file.write(line + "\n")  # Add newline after the line
    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")
        return

    print(f"Line saved to {filename} (append={append}): {line}")

# Build the standard command string for sending
def build_cmd():
    global cmd, tower, dly_cmd, tower_curr, max_tower
    if rotation_mode:
        if tower_curr > max_tower:
            tower_curr = 1  # Reset tower rotation

    strcmd = cmd + "," + str(tower_curr) + "," + str(dly_cmd)

    if rotation_mode:
        tower_curr += 1  # Increment for next rotation

    return strcmd

# Build a command string using a specified message and tower
def build_cmd_line(msg, twr):
    global dly_cmd
    return msg + "," + str(twr) + "," + str(dly_cmd)


def breakdownfields(_str):
    """
    Assumes the string has a format like '...@value1,value2,value3'
    Returns the first two values as integers and the third as a string.
    """
    section = _str.split("@")
    testing = section[1].split(",")
    return int(testing[0]), int(testing[1]), testing[2]

# Compares a substring of _rx to a reference string
def comparevalues(_rx, _from, _to, _ref):
    if _rx[_from:_to] == _ref:
        return "o"  # Match OK
    else:
        return f"error: rx = {_rx[_from:_to]} DIFFERENT TO {_ref}"
    
class GGCCSS(QWidget):
    # Signal definitions to emit log data (int and str)
    eventlogInt = pyqtSignal(int)
    eventlogStr = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS")  # Set window title

        # Window geometry
        self.left = 200
        self.top = 100
        self.width = 2800
        self.height = 2000
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Main vertical layout for stacking components top to bottom
        self.main_layout = QVBoxLayout()
        self.h_layout0 = QHBoxLayout()  # Header row for labels
        self.h_layout1 = QHBoxLayout()  # Row for combo boxes and status label
        self.h_layout2 = QHBoxLayout()  # Row for checkboxes and control buttons

        # Title label
        self.voltage_label = QLabel("G r o u n d    C o n t r o l    S t a t i o n")
        self.voltage_label.setAlignment(Qt.AlignCenter)
        self.voltage_label.setStyleSheet("font-size: 68px;font-weight: bold;italic;")
        self.main_layout.addWidget(self.voltage_label)

        # Subheading
        self.unit_label = QLabel("System configuration, verification, regression test, POST (Power On Self Test) and readiness")
        self.unit_label.setAlignment(Qt.AlignCenter)
        self.unit_label.setStyleSheet("font-size: 36px;")
        self.main_layout.addWidget(self.unit_label)

        # RSSI display label
        self.value_label = QLabel("-.-- dBm")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 65px; font-weight: bold;color: green; background-color: black;")
        self.palette1 = self.value_label.palette()
        self.palette1.setColor(QPalette.WindowText, QColor("green"))
        self.value_label.setPalette(self.palette1)
        self.main_layout.addWidget(self.value_label)

        # Header row with 5 labels
        self.label1 = QLabel("         ", self)
        self.label2 = QLabel("Select", self)
        self.label3 = QLabel("Command", self)
        self.label4 = QLabel("Rx delay (mS)", self)
        self.label5 = QLabel("Timer (mS)", self)
        for label in [self.label1, self.label2, self.label3, self.label4, self.label5]:
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 48px; font-weight: bold;")
            self.h_layout0.addWidget(label)
        self.main_layout.addLayout(self.h_layout0)

        # Status label (updates with selection)
        self.label = QLabel("-", self)
        self.label.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.h_layout1.addWidget(self.label)

        # ComboBox 1: Tower selection
        self.combo1 = QComboBox(self)
        self.combo1.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.combo1.addItems(["Ground Control Station","Tower # 1", "Tower # 2", "Tower # 3", "Tower # 4"])
        self.combo1.setCurrentIndex(tower)
        self.combo1.currentIndexChanged.connect(self.on_combobox1_changed)
        self.h_layout1.addWidget(self.combo1)

        # ComboBox 2: Command selection
        self.combo2 = QComboBox(self)
        self.combo2.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.combo2.addItems(["idn?","rssi?", "dl?", "ul?", "rec?","adc?","rly?","dout?"])
        self.combo2.setCurrentIndex(0)
        self.combo2.currentIndexChanged.connect(self.on_combobox2_changed)
        self.h_layout1.addWidget(self.combo2)

        # ComboBox 3: Rx delay
        self.combo3 = QComboBox(self)
        self.combo3.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.combo3.addItems(["0","50", "80", "150", "200", "250", "300", "400"])
        self.combo3.setCurrentIndex(4)
        self.combo3.currentIndexChanged.connect(self.on_combobox3_changed)
        self.h_layout1.addWidget(self.combo3)

        # ComboBox 4: Timer delay
        self.combo4 = QComboBox(self)
        self.combo4.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.combo4.addItems(["0", "50", "250", "500", "650", "750", "1000", "2000", "10000"])
        self.combo4.setCurrentIndex(7)
        self.combo4.currentIndexChanged.connect(self.on_combobox4_changed)
        self.h_layout1.addWidget(self.combo4)

        self.main_layout.addLayout(self.h_layout1)

        # Log display area (readonly QTextEdit)
        self.logOutput = QTextEdit()
        self.logOutput.setReadOnly(True)
        self.logOutput.setLineWrapMode(QTextEdit.NoWrap)
        self.font = QFont("Consolas", 18)
        self.font.setStyleHint(QFont.TypeWriter)
        self.logOutput.setCurrentFont(self.font)
        self.logOutput.setStyleSheet("background-color: black;")
        self.logOutput.setTextColor(QColor(255, 0, 0))
        self.main_layout.addWidget(self.logOutput)

        # Checkbox: Auto/manual toggle
        self.checkbox = QCheckBox("Auto/ manual")
        self.checkbox.setChecked(False)
        self.checkbox.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.checkbox.stateChanged.connect(self.checkbox_changed)

        # Checkbox: Rotation mode
        self.checkbox2 = QCheckBox("Rotation Mode")
        self.checkbox2.setChecked(False)
        self.checkbox2.setStyleSheet("font-size: 48px; font-weight: bold;")
        self.checkbox2.stateChanged.connect(self.checkboxRotation_changed)

        # Button: STOP
        self.buttonSTOP = QPushButton("STOP", self)
        self.buttonSTOP.setStyleSheet("color: red; background-color: white;")
        self.buttonSTOP.setFont(QFont('Times', 11, QFont.Bold))
        self.buttonSTOP.clicked.connect(self.clicked_STOP)

        # Button: Start continuous GCS thread
        self.button1 = QPushButton("Continuous Query", self)
        self.button1.setStyleSheet("color: green; background-color: white;")
        self.button1.setFont(QFont('Times', 11, QFont.Bold))
        self.button1.clicked.connect(self.clicked_GCS1)

        # Button: Run command sequence
        self.button2 = QPushButton("Run a sequence", self)
        self.button2.setStyleSheet("color: green; background-color: white;")
        self.button2.setFont(QFont('Times', 11, QFont.Bold))
        self.button2.clicked.connect(self.clicked_GCS2)

        # Add all controls to layout
        for widget in [self.checkbox, self.checkbox2, self.buttonSTOP, self.button1, self.button2]:
            self.h_layout2.addWidget(widget)
        self.main_layout.addLayout(self.h_layout2)

        # Finalize layout
        self.setLayout(self.main_layout)

        # Timer to periodically update RSSI
        self.timer1 = QTimer(self)
        self.timer1.timeout.connect(self.update_rssi)

    def logInt(self, val):
        self.logOutput.insertPlainText(str(val) + "\n")

    # Start continuous polling thread
    def startSRThread_GCS1(self):
        self.SRThread_GCS1 = SRThread_GCS1()
        self.SRThread_GCS1.eventlogInt.connect(self.logInt)
        self.SRThread_GCS1.eventlogStr.connect(self.logStr)
        self.SRThread_GCS1.start()

    # Start command sequence thread
    def startSRThread_GCS2(self):
        self.SRThread_GCS2 = SRThread_GCS2()
        self.SRThread_GCS2.eventlogInt.connect(self.logInt)
        self.SRThread_GCS2.eventlogStr.connect(self.logStr)
        self.SRThread_GCS2.start()

    # Button: Start continuous mode    
    def clicked_GCS1(self):
        global thr_running
        thr_running = True
        self.logStr("...Started Continuous Query Thread")
        self.startSRThread_GCS1()
    
    # Button: Start sequence
    def clicked_GCS2(self):
        global thr_running
        thr_running = True
        self.logStr("...Started Sequence execution Thread")
        self.startSRThread_GCS2()

    # Button: STOP all threads
    def clicked_STOP(self):
        global thr_running
        thr_running = False
        self.logStr("...Stop all threads")

    def logStr(self, val):  # self.logOutput.moveCursor(QTextCursor.End)
        # self.logOutput.moveCursor(QTextCursor.End)
        # self.logOutput.insertPlainText(str(val) + "\n")
        self.logOutput.append(str(val))
        print(val + '\n')
    def on_combobox1_changed(self, index): #tower #
        global tower
        selected_text = self.combo1.itemText(index)
        self.label.setText(f"Selected: {selected_text}")
        print(f"Combo box changed to index {index}: {selected_text}")
        tower = index
    def on_combobox2_changed(self, index):
        global cmd
        selected_text = self.combo2.itemText(index)
        self.label.setText(f"Selected: {selected_text}")
        print(f"Combo box changed to index {index}: {selected_text}")
        cmd = selected_text
    def on_combobox3_changed(self, index):
        global dly_cmd
        selected_text = self.combo3.itemText(index)
        self.label.setText(f"Selected: {selected_text}")
        print(f"Combo box changed to index {index}: {selected_text}")
        dly_cmd = int(selected_text)
    def on_combobox4_changed(self, index): #timer delay
        global dly_comm
        selected_text = self.combo4.itemText(index)
        self.label.setText(f"Selected: {selected_text}")
        print(f"Combo box changed to index {index}: {selected_text}")
        dly_comm = int(selected_text)
    def checkbox_changed(self, state):
        global auto,sync_flg
        print("sync_flg = " + str(sync_flg))
        sync_flg = True
        if state == Qt.Checked:
            auto = True
            mf.timer1.start(dly_comm)
        else:
            auto = False
            mf.timer1.stop()

    def checkboxRotation_changed(self, state):
        global rotation_mode
        if state == Qt.Checked:
            rotation_mode = True
        else:
            rotation_mode = False
        print("rotation_mode = " + str(rotation_mode))

    def update_rssi(self):
        global serial_port
        """Generates a random voltage value and updates the display."""
        #voltage = random.uniform(0.0, 15.0)  # Generate random voltage between 0.0 and 15.0
        self.value_label.setText(f"{rssi:.0f} dBm")

# GCS1 ///////////////////////////////////////////////////////////////////////////////////
# Thread class responsible for bidirectional serial communication for GCS1
class SRThread_GCS1(QThread):
    # Define signals to communicate with GUI (if any)
    eventlogInt = pyqtSignal(int)
    eventlogStr = pyqtSignal(str)

    # Set thread running flag to true
    global serial_connection, receive_thread, send_thread, rssi, station, RMODE, thr_running
    thr_running = True

    def receive_data(self):
        """ Continuously receives data from serial port and processes it. """
        global serial_connection, receive_thread, send_thread, rssi, station, RMODE, filename, sync_flg

        while thr_running:
            try:
                if serial_connection.in_waiting > 0:
                    # Read a line of data from serial port
                    received_bytes = serial_connection.readline()
                    sync_flg = True  # Signal that a sync-able message was received
                    try:
                        # Decode and strip the newline
                        received_text = received_bytes.decode('utf-8').strip()
                        print(f"{received_text}")
                        
                        # Case 1: Data is a numeric RSSI value
                        if len(received_text) > 0 and is_number(received_text):
                            rssi = float(received_text)
                            self.logRow(received_text)

                        # Case 2: Data is a comma-separated string (e.g., telemetry)
                        elif len(received_text) > 0:
                            self.logRow(received_text)
                            try:
                                open(filename, 'a').close()  # Ensure file exists
                            except Exception as e:
                                print(f"Error creating file: {e}")

                            fields = received_text.split(',')
                            # Recieved text is the data in form of 1,2,34,2025-04-20 16:55:12,12.1234567,123.123456,12.98
                            # first # is the record number and the second one is the tower id 
                            if len(fields) == 7:
                                # Log data
                                save_string_line(filename, received_text, append=True)

                                # Send ACK
                                text_to_send = build_cmd_line("ack", fields[1]) + "\r\n"
                                serial_connection.write(text_to_send.encode('utf-8'))
                                serial_connection.flush()
                                print(f"Sent: {text_to_send}")
                    except UnicodeDecodeError:
                        print(f"Received non-UTF-8 data: {received_bytes}")
            except serial.SerialException as e:
                print(f"Error reading from serial port: {e}")
                break

            time.sleep(0.1)

        serial_connection.close()


    def send_data(self):
        """ Continuously sends commands over serial port in auto mode. """
        global serial_connection, receive_thread, send_thread, rssi, station, RMODE, auto, sync_flg

        while thr_running:
            if auto:
                try:
                    if sync_flg:
                        # Clear buffers and send command
                        serial_connection.reset_output_buffer()
                        serial_connection.reset_input_buffer()
                        serial_connection.flushInput()
                        serial_connection.flushOutput()

                        text_to_send = build_cmd() + "\r\n"
                        serial_connection.write(text_to_send.encode('utf-8'))

                        # Update sync flag depending on command
                        sync_flg = True if text_to_send[:3] == "ack" else False

                        serial_connection.flush()
                        print(f"Sent: {text_to_send}")
                        time.sleep(dly_comm / 1000)
                        print("Clearing flag when cmd: " + text_to_send)
                except serial.SerialException as e:
                    print(f"Error writing to serial port: {e}")
                    break
            else:
                time.sleep(1)

        print("Sending thread stopped.")
        serial_connection.close()

    def logRow(self, txt):
        """ Emit string signal for GUI or console logging. """
        self.eventlogStr.emit(txt)

    def run(self):
        """ Entry point for the QThread: initializes serial connection and launches threads. """
        print("GCS ... started\n")
        print("\n--- File Contents ---")
        try:
            with open(filename, "r") as file:
                print(file.read())
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except Exception as e:
            print(f"An error occurred reading the file: {e}")

        global serial_connection, receive_thread, send_thread
        try:
            serial_connection = serial.Serial(port, baudrate, timeout=3)
            time.sleep(0.6)
            print(f"Connected to {port} at {baudrate} bps")

            # Start receiver thread
            receive_thread = threading.Thread(target=self.receive_data)
            receive_thread.daemon = True
            receive_thread.start()
            print("Receive thread active\n")

            # Start sender thread
            send_thread = threading.Thread(target=self.send_data, args=serial_connection)
            send_thread.start()
            print("Sending thread active\n")
            send_thread.join()  # Wait until sending thread ends

        except serial.SerialException as e:
            print(f"Error opening serial port {port}: {e}")
        finally:
            if serial_connection and serial_connection.is_open:
                print(f"Keep serial port {port} open")

        time.sleep(1)
        self.logRow("Thread ended\n")

# GCS2 ///////////////////////////////////////////////////////////////////////////////////
def wait_for_newline():
    """ Waits for a newline-terminated string from the serial port. """
    global serial_connection
    timeout = None
    try:
        received_data = b""
        while True:
            byte = serial_connection.read(1)
            if byte == b"":
                if timeout is not None:
                    print("Timeout occurred while waiting for data.")
                    serial_connection.close()
                    return None
                continue
            received_data += byte
            if byte == b'\n':
                break
        return received_data.decode('utf-8').rstrip('\n').rstrip('\r')

    except serial.SerialException as e:
        print(f"Error reading from serial port {port}: {e}")
        serial_connection.close()
        return None

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        serial_connection.close()
        return None

    finally:
        print("done receiving")


class SRThread_GCS2(QThread):
    eventlogInt = pyqtSignal(int)
    eventlogStr = pyqtSignal(str)

    global serial_connection, receive_thread, send_thread, rssi, station, RMODE, thr_running
    thr_running = True

    def logRow(self, txt):
        """ Emit string signal for logging. """
        self.eventlogStr.emit(txt)

    def run(self):
        """ Executes a sequence of commands from a script file over serial. """
        global Sequence_script
        global serial_connection, receive_thread, send_thread

        # Load and parse the command script file
        loaded_string = load_string_from_file(Sequence_script)
        try:
            serial_connection = serial.Serial(port, baudrate, timeout=3)
            serial_connection.flushOutput()
            serial_connection.flushInput()
            serial_connection.reset_output_buffer()
            serial_connection.reset_input_buffer()
            time.sleep(0.6)
            print(f"Connected to {port} at {baudrate} bps")

            fields = loaded_string.split("\n")
            for item in fields:
                # Clean up item string
                item = item.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
                print("isnumeric?{" + item + "}")
                if is_number(item):
                    # Delay in seconds
                    print("delay (Sec) : " + item)
                    time.sleep(float(item))
                elif len(item) > 0:
                    # Send command
                    text_to_send = item + "\r\n"
                    self.logRow(item)
                    serial_connection.write(text_to_send.encode('utf-8'))
                    serial_connection.flush()
                    sync_flg = True if text_to_send[:3] == "ack" else False

                    print(f"Sent: {text_to_send}")
                    received_text = wait_for_newline()
                    print(received_text)
                    self.logRow("\t\t" + received_text)
                    sync_flg = True

        except serial.SerialException as e:
            print(f"Error opening serial port {port}: {e}")
        finally:
            if serial_connection and serial_connection.is_open:
                serial_connection.close()
                print(f"Keep serial port {port} open")

        time.sleep(1)
        self.logRow("Thread ended\n")


# Wrap up ////////////////////////////////////////////////////////
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mf = GGCCSS()
    mf.show()
    sys.exit(app.exec_())
    send_thread.join()
