import serial
import threading
import time
import subprocess
import re

port = '/dev/tty.usbserial-0001'
port = '/dev/tty.usbserial-6'
baudrate = 115200 
b_tx_was_ack = True
serial_ack = "GCSackS" # form that the python code will recieve the GCS ack 
serial_req = "GCSrec" # form that the python code will recieve the GCS req for data
num_records_to_send = 0

## looks for the data to have pattern
# "99           2            10           2025-05-09T16:35:04.592986 32.8815142   117.2349313  4.11       0"
pattern = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+"
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s*$"
)

#checks if the recieved text is an ack or a request
def handle_recieving_ack_and_rec(received_text):
    global b_tx_was_ack
    global num_records_to_send
    if serial_ack in received_text:
        b_tx_was_ack = True
    elif serial_req in received_text:
        #sets the number of records the python code should send
        num_records_to_send = int(received_text.split(",")[1])


    

def receive_data(serial_port):
    """Continuously reads data from the serial port and prints it."""
    while True:
        try:
            if serial_port.in_waiting > 0:
                received_bytes = serial_port.readline()  # Read until newline (\n)
                #received_bytes = serial_port.read(serial_port.in_waiting)
                try:
                    received_text = received_bytes.decode('utf-8').strip()
                    handle_recieving_ack_and_rec(received_text)
                    print(f"{received_text}")
                except UnicodeDecodeError:
                    print(f"Received non-UTF-8 data: {received_bytes}")
        except serial.SerialException as e:
            print(f"Error reading from serial port: {e}")
            break
        time.sleep(0.1)  # Small delay to avoid busy-waiting


def handling_transmitting(serial_port):
    global b_tx_was_ack
    global num_records_to_send
    print("Starting to read data generator")
    process = subprocess.Popen(
        ["python3", "/Users/williamgong/Desktop/WES/Final_project/WES207-main/tower2/dataGenerator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    #loops through the data line by line
    for line in process.stdout:
        match = pattern.match(line)
        #check if it the output is actually data
        if not match: continue
        #wait until if the data tx was not acknowledged or finished the request amount of data
        while not b_tx_was_ack or not num_records_to_send:
            time.sleep(.1) 
            pass
        if line: 
            print("Forwarding:", line.strip())
            serial_port.write(("data " + line.strip() + '\n').encode('utf-8'))
            serial_port.flush()
            b_tx_was_ack = False
            num_records_to_send = num_records_to_send -1
            time.sleep(.1)
    return 
    
    

def send_data(serial_port):
    global b_tx_was_ack
    """Continuously prompts the user for input and sends it over the serial port."""
    while True:
        try:
            serial_port.reset_output_buffer()
            serial_port.reset_input_buffer()
            serial_port.flushInput()
            serial_port.flushOutput()
            #do not run if there are no records to send
            #TODO not too sure if the hand transmitting should be in a while loop though.
            if num_records_to_send: handling_transmitting(serial_port)
            #text_to_send = "idn?,4,200\r\n"
            ##text_to_send = input("Enter command: ")
            ##serial_port.write(text_to_send.encode('utf-8')) 
            #serial_port.flush()
            #print(f"Sent: {text_to_send}")

            time.sleep(1)

        except serial.SerialException as e:
            print(f"Error writing to serial port: {e}")
            break
    #time.sleep(1)
    print("Sending thread stopped.")

def main():
    serial_connection = None


    try:
        print(f"Trying to connect")
        serial_connection = serial.Serial(port, baudrate, timeout=3)
        print(f"Connected to {port} at {baudrate} bps")

        # Create and start the receiver thread
        receive_thread = threading.Thread(target=receive_data, args=(serial_connection,))
        receive_thread.daemon = True  # Allow main thread to exit even if this is running
        receive_thread.start()

        # Create and start the sender thread
        send_thread = threading.Thread(target=send_data, args=(serial_connection,))
        send_thread.start()
        send_thread.join()  # Wait for the sending thread to finish (when user enters 'quit')

    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
    finally:
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
            print(f"Closed serial port {port}")

if __name__ == "__main__":
    main()
