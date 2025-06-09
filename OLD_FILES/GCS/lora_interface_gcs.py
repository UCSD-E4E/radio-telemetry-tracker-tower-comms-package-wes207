import serial
import threading
import time
import os

port = '/dev/tty.usbserial-0001'
#port = '/dev/tty.usbserial-2'
baudrate = 115200
b_data_was_recorded = False
data_flag = "data" #data to be recorded have data out in front
num_of_records_requested = 4 #number of records to request teh towers
num_of_rec_recieved = 0 #current count of records recieved per request
num_of_towers = 2 #number of towers to collect from

LOG_FILE = "data_log.txt"

#Writes the data to the file, tries to handle is something was disconnected suddenly
def write_line_secure(file, line):
    global b_data_was_recorded
    try:
        file.write(line + "\n")
        file.flush()  
        os.fsync(file.fileno())
        b_data_was_recorded = True
    except Exception as e:
        print(f"Write failed: {e}")
        raise

#sends the acknowledge in form of "ack,<tower_id>,0"
def data_was_recorded(serial_port,data):
    global b_data_was_recorded
    global num_of_rec_recieved
    if b_data_was_recorded:
        #tower_id = hex(int(data.split()[1]))
        tower_id = int(data.split()[1])
        ack_cmd = "ack," + str(tower_id) + ",0\n"
        serial_port.write(ack_cmd.encode('utf-8'))
        serial_port.flush()
        b_data_was_recorded = False
        num_of_rec_recieved += 1
        ##print("RECORDED")



def receive_data(serial_port):
    global data_flag
    """Continuously reads data from the serial port and prints it."""
    try:
        with open(LOG_FILE, "a", buffering=1) as f:
            while True:
                try:
                    if serial_port.in_waiting > 0:
                        received_bytes = serial_port.readline()  # Read until newline (\n)
                        #received_bytes = serial_port.read(serial_port.in_waiting)
                        try:
                            received_text = received_bytes.decode('utf-8').strip()
                            print(f"{received_text}")

                            if data_flag in received_text:
                                data = received_text.replace(data_flag,'') 
                                write_line_secure(f, data)
                                data_was_recorded(serial_port, data)

                        except UnicodeDecodeError:
                            print(f"Received non-UTF-8 data: {received_bytes}")
                except serial.SerialException as e:
                    print(f"Error reading from serial port: {e}")
                    break
    except KeyboardInterrupt:
        print("\nLogger stopped by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        time.sleep(0.1)  # Small delay to avoid busy-waiting

#sends request to towers in form of "rec?,<tower number>,<number_of_records>"
#loops through the towers.
# TODO needs to handle if the towers are taking too long and move to another one
def send_data_requests_to_towers(serial_port):
    global num_of_records_requested
    global num_of_rec_recieved
    global num_of_towers
    start = input("press anything to start: ")
    while True:
        try:
            for tower in range(1,num_of_towers + 1):
                num_of_rec_recieved = 0
                serial_port.reset_output_buffer()
                serial_port.reset_input_buffer()
                serial_port.flushInput()
                serial_port.flushOutput()
                text_to_send = "rec?," + str(tower) + "," + str(num_of_records_requested) + "\n"
                serial_port.write(text_to_send.encode('utf-8'))
                serial_port.flush()
                print(f"Sent: {text_to_send}")
                while num_of_rec_recieved < num_of_records_requested:
                    time.sleep(.1)
                time.sleep(2)
        except serial.SerialException as e:
            print(f"Error writing to serial port: {e}")
            break
    #time.sleep(1)
    print("Sending thread stopped.")


def send_data(serial_port):
    """Continuously prompts the user for input and sends it over the serial port."""
    while True:
        try:
            serial_port.reset_output_buffer()
            serial_port.reset_input_buffer()
            serial_port.flushInput()
            serial_port.flushOutput()
            #data_was_recorded(serial_port)
            #text_to_send = "idn?,4,200\r\n"
            text_to_send = input("Enter command: ")
            serial_port.write(text_to_send.encode('utf-8'))
            serial_port.flush()
            print(f"Sent: {text_to_send}")
            time.sleep(2)
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
        #send_thread = threading.Thread(target=send_data, args=(serial_connection,))
        #send_thread.start()
        #send_thread.join()  # Wait for the sending thread to finish (when user enters 'quit')

        send_rec_for_data_thread = threading.Thread(target=send_data_requests_to_towers, args=(serial_connection,))
        send_rec_for_data_thread.start()
        send_rec_for_data_thread.join()  # Wait for the sending thread to finish (when user enters 'quit')

    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
    finally:
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
            print(f"Closed serial port {port}")

if __name__ == "__main__":
    main()
