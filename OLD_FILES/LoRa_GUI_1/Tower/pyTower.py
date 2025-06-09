import serial, random, threading, time, datetime, subprocess, re, sys



# Global variables
ack_flag = False                    # Tracks if an acknowledgment has been received
b_tx_was_ack = True                 # Tracks if an acknowledgment has been received
b_first_time_call = False           # Tracks if first python data gen script was called
port = 'COM8'  
port = '/dev/tty.usbserial-2'    # Inital serial port (change depending on OS)
baudrate = 115200                  # Baud rate for serial communication

#Used right now to generate random data
recno = 0                          # Record number counter
tower = "1"                        # Tower ID (string format)

multirec_mode = False              # Flag for multi-record transfer mode
rec_pending = False                # Flag to track if records are pending to be sent
rec_transf_max = 5                 # Max number of records to transfer
rec_cntr = 0                       # Record transfer counter

# Generate a random number between `min` and `max` with `decdigits` decimal places
def gen_rnd(min, max, decdigits):
    integer_part = random.randint(min, max)
    decimal_part = round(random.random(), decdigits)
    return str(integer_part + decimal_part)

# Returns the current timestamp in "YYYY-MM-DD HH:MM:SS" format
def timestamp():
    timestamp = time.time()
    dt_object = datetime.datetime.fromtimestamp(timestamp)
    date_string = dt_object.strftime("%Y-%m-%d")
    time_string = dt_object.strftime("%H:%M:%S")
    return date_string + " " + time_string

pattern = re.compile(
    r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+'
    r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+'
    r'(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$'
)

def get_next_data(process, serial_port):
    global b_tx_was_ack
    for line in process.stdout:
        match = pattern.match(line)
        #check if it the output is actually data
        if not match: continue
        if line:
            print(line)
            data = str(",".join(line.strip().split()))
            #print(data)
            time.sleep(.5)
            yield data


def handling_transmitting(serial_port):
    global b_tx_was_ack, b_first_time_call, process


    #loops through the data line by line
    data = next(get_next_data(process, serial_port))
    print("Forwarding:", data)
    serial_port.write((data + '\r\n').encode('utf-8'))
    serial_port.flush()
    return 
    

# Thread function to handle receiving data over serial port. This is from the Lora Device
def receive_data(serial_port):
    global recno, tower, multirec_mode, rec_pending, rec_transf_max, rec_cntr, b_tx_was_ack
    while True:
        try:
            if serial_port.in_waiting > 0:
                # Read available data until newline character
                received_bytes = serial_port.readline()
                try:
                    received_text = received_bytes.decode('utf-8').strip()
                    print(f"{received_text}")

                    # If device requests a record
                    if received_text[:4] == "rec?":
                        # Flush buffers before sending
                        serial_port.reset_output_buffer()
                        serial_port.reset_input_buffer()
                        serial_port.flushInput()
                        serial_port.flushOutput()

                        # Generate and send a fake record
                        #msg = str(recno) + "," + tower + "," + gen_rnd(1, 30, 0) + "," + timestamp() + "," + gen_rnd(21, 34, 7) + "," + gen_rnd(110, 133, 7) + "," + gen_rnd(17, 28, 2)
                        #text_to_send = msg + "\r\n"
                        #print("... sent record: " + msg)
                        #serial_port.write(text_to_send.encode('utf-8'))
                        #serial_port.flush()
                        handling_transmitting(serial_port)
                        time.sleep(0.08)

                        recno += 1
                        rec_cntr = 1

                    # Confirmation that record was received by LoRa device
                    elif received_text[:2] == "ok":
                        print("... ... {ok} received record into LoRa device")
                        #ack_flag = True
                        b_tx_was_ack = True

                    # ACK from ground control station
                    elif received_text[:3] == "ack":
                        print("... ... ... {ack} received from GCS")
                        #ack_flag = False  # Clear ACK flag for next record
                        b_tx_was_ack = True

                        # If in multirecord mode and more records are pending
                        if multirec_mode and rec_pending:
                            # Same process to send another record
                            serial_port.reset_output_buffer()
                            serial_port.reset_input_buffer()
                            serial_port.flushInput()
                            serial_port.flushOutput()

                            #msg = str(recno) + "," + tower + "," + gen_rnd(1, 30, 0) + "," + timestamp() + "," + gen_rnd(21, 34, 7) + "," + gen_rnd(110, 133, 7) + "," + gen_rnd(17, 28, 2)
                            #text_to_send = msg + "\r\n"
                            #print("... sent record: " + msg)
                            #serial_port.write(text_to_send.encode('utf-8'))
                            #serial_port.flush()
                            handling_transmitting(serial_port)
                            time.sleep(0.08)
                            
                            recno += 1
                            rec_cntr += 1
                            time.sleep(1)

                            if rec_cntr > rec_transf_max:
                                rec_pending = False  # Stop sending more records

                except UnicodeDecodeError:
                    print(f"Received non-UTF-8 data: {received_bytes}")
        except serial.SerialException as e:
            print(f"Error reading from serial port: {e}")
            break
        time.sleep(0.1)  # Avoid busy-waiting

# Thread function to send periodic data or commands over serial (currently disabled)
def send_data(serial_port):
    send_anything = False  # Toggle this to True to enable periodic sending
    while True:
        if send_anything:
            try:
                serial_port.reset_output_buffer()
                serial_port.reset_input_buffer()
                serial_port.flushInput()
                serial_port.flushOutput()

                text_to_send = "idn?\r\n"
                serial_port.write(text_to_send.encode('utf-8'))
                serial_port.flush()
                print(f"Sent: {text_to_send}")
                time.sleep(5)

            except serial.SerialException as e:
                print(f"Error writing to serial port: {e}")
                break
        time.sleep(1)
    print("Sending thread stopped.")

# Main function to establish connection and start threads
def main():
    global process

    serial_connection = None
    try:

        print("Starting to read data generator")
        process = subprocess.Popen(
            ["python3", "/Users/williamgong/Desktop/WES/Final_project/data_code/runme.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        serial_connection = serial.Serial(port, baudrate, timeout=3)
        print(f"Connected to {port} at {baudrate} bps")

        # Start receiving thread
        receive_thread = threading.Thread(target=receive_data, args=(serial_connection,))
        receive_thread.daemon = True
        receive_thread.start()

        # Start sending thread
        send_thread = threading.Thread(target=send_data, args=(serial_connection,))
        send_thread.start()
        send_thread.join()  # Wait for sending thread to finish (if ever)

    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
    finally:
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
            print(f"Closed serial port {port}")

# Run the program
if __name__ == "__main__":
    main()
