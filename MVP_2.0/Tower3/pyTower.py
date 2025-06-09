#pyTower.py
#This handles communication between the database and LoRa device
#Be sure to set the correct port.
import serial
import threading
import time
import database, towerConfig

class LoRaCommunicator:
    def __init__(self, database_lock):
        self.database_lock = database_lock              #lock for accessing database (from runme.py)
        self.baudrate = 115200                          #baudrate
        self.serial_connection = None
        self.database = database.TowerDatabase()        #object for accessing database
        self.running = False                            #end threads when False
        self.pending_record = None
        self.pending_sample_num = None
        self.waiting_for_ack = False
        
        #Set port for serial comms with heltec based on OS/port. DO THIS UPON SETUP!
        self.port = 'COM5'                              # Serial port (windows), use device manager to change port to COMXX
        #self.port = '/dev/ttyUSB0'                     # Serial port on Ubuntu. $ls /dev/tty* 
        #self.port = '/dev/tty.usbserial-2'             # Serial port for mac

        # Statistics for shutdown monitoring
        self.records_sent = 0
        self.acks_received = 0
        self.timeouts = 0
        
    def start_communication(self):
        """Main communication loop. Called by runme.py. Establishes serial comms with Heltec and creates threads for sending and receiving serial comms"""
        try:
            # Open serial connection
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"LoRa: Connected to {self.port} at {self.baudrate} bps")
            self.running = True
            
            # Start receive thread
            receive_thread = threading.Thread(target=self._receive_handler, daemon=True)
            receive_thread.start()
            
            # Main sending loop
            self._main_send_loop()
            
        except serial.SerialException as e:
            print(f"LoRa: Error opening serial port {self.port}: {e}")
        finally:
            self.stop_communication()
    
    def _main_send_loop(self):
        """Main loop that sends records from database to Heltec. Handle timing, timout, & sending while waiting for ack."""
        last_send_time = 0   # Timestamp of last send attempt
        send_interval = 2.0  # seconds between attempts
        ack_timeout = 10.0   # seconds to wait for ACK
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check for ACK timeout
                if self.waiting_for_ack and (current_time - last_send_time > ack_timeout):
                    print(f"LoRa: ACK timeout for record #{self.pending_sample_num}")
                    self.timeouts += 1
                    self.waiting_for_ack = False
                    self.pending_record = None
                    self.pending_sample_num = None
                    if self.database_lock.locked():
                        try:
                            self.database_lock.release()
                            print(f"Released database lock after timeout of {ack_timeout} seconds.")
                        except RuntimeError as e: #Another thread might hold the lock, so print runtime error as possibility.
                            print(f"Attempted to release database lock after timeout but another thread holds the lock: {e}")
                
                # Only try to send if not waiting for ACK and enough time has passed
                if not self.waiting_for_ack and (current_time - last_send_time >= send_interval):
                    if self._send_next_record():
                        last_send_time = current_time
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"LoRa: Error in main send loop: {e}")
                time.sleep(1)
    
    def _send_next_record(self):
        """Get and send the next record from database. Return true if sent successfully, false failed or if no data to send."""
        try:
            # Try to acquire database lock (blocking). Give up trying after timeout seconds.
            self.database_lock.acquire(blocking=True, timeout=5)
            
            try:
                # Get first record from database
                record_string, sample_num = self.database.print_first_row()
                
                if record_string and sample_num:
                    print(f"LoRa: Retrieved record #{sample_num} from database")
                    print(f"LoRa: Forwarding record #{sample_num}: {record_string}")
                    
                    # Send the record
                    if self._send_record(record_string):
                        self.pending_record = record_string
                        self.pending_sample_num = sample_num
                        self.waiting_for_ack = True
                        self.records_sent += 1
                        print(f"LoRa: Holding database lock until ACK received for record #{sample_num}")
                        return True
                    else:
                        print(f"LoRa: Failed to send record #{sample_num}")
                        return False
                else:
                    # No records in database
                    return False
                    
            finally:
                # Only release lock if we're not waiting for ACK
                if not self.waiting_for_ack:
                    self.database_lock.release()
                    
        except Exception as e:
            print(f"LoRa: Error getting record from database: {e}")
            if self.database_lock.locked():
                self.database_lock.release()
            return False
    
    def _send_record(self, record_string):
        """Send a record over serial to Heltec. Clear buffers. Return true if sent correctly, false if error."""
        try:
            if not self.serial_connection or not self.serial_connection.is_open:
                return False
            
            # Clear buffers
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Send the record
            message = record_string + '\r\n'
            self.serial_connection.write(message.encode('utf-8'))
            self.serial_connection.flush()
            
            return True
            
        except serial.SerialException as e:
            print(f"LoRa: Error sending record: {e}")
            return False
    
    def _receive_handler(self):
        """Handle incoming serial data commands from GCS to tower. Always runs until self.running set to False. """
        while self.running:
            try:
                if self.serial_connection and self.serial_connection.in_waiting > 0:
                    # Read  line from serial (blocks until \n received)
                    received_bytes = self.serial_connection.readline()
                    
                    try:
                         # Decode bytes to string and remove whitespace
                        received_text = received_bytes.decode('utf-8').strip()
                        if received_text:
                            print(f"LoRa: Received: {received_text}")
                            self._process_received_message(received_text)
                            
                    except UnicodeDecodeError:
                        print(f"LoRa: Received non-UTF-8 data: {received_bytes}")
                
                time.sleep(0.1)
                
            except serial.SerialException as e:
                print(f"LoRa: Error reading from serial: {e}")
                break
            except Exception as e:
                print(f"LoRa: Error in receive handler: {e}")
                time.sleep(1)
    
    def _process_received_message(self, message):
        """Process received messages from LoRa device. Commands (like ack, rec?, etc) are here. message is the message from GCS. If you want to add more commands, do it here."""
        try:
            # Handle record request
            if message.startswith("rec?"):
                print("LoRa: Received record request (rec?)")
                # This could trigger immediate send, but we're using continuous sending
                
            # Handle "ok" - LoRa device received the record thru serial
            elif message.startswith("ok"):
                print("LoRa: ... {ok} LoRa device received the record from database.")
                # After this, wait for the ack message
                
            # Handle "ack" - Ground control station acknowledged
            elif message.startswith("ack"):
                print("LoRa: ... ... {ack} received from Ground Control Station")
                self._handle_ack()
                
            # Handle other messages
            else:
                print(f"LoRa: Unknown message: {message}")
                
        except Exception as e:
            print(f"LoRa: Error processing message '{message}': {e}")
    
    def _handle_ack(self):
        """Handle ACK here: Delete record from database & release lock."""
        try:
            if self.waiting_for_ack and self.pending_sample_num:
                # Database lock should already be held from _send_next_record()
                # Delete the acknowledged record
                deleted_count = self.database.delete_ack(self.pending_sample_num)
                if deleted_count > 0:
                    print(f"LoRa: Successfully deleted record #{self.pending_sample_num} from database")
                    self.acks_received += 1
                else:
                    print(f"LoRa: Warning - Record #{self.pending_sample_num} not found for deletion")
                
                # Clear pending state and release the lock
                self.waiting_for_ack = False
                self.pending_record = None
                self.pending_sample_num = None
                self.database_lock.release()
                print("LoRa: Released database lock after ACK processing")
            else:
                print("LoRa: Received ACK but no pending record")
                
        except Exception as e:
            print(f"LoRa: Error handling ACK: {e}")
            # Make sure to release lock on error if we were waiting for ACK
            if self.waiting_for_ack:
                try:
                    self.database_lock.release()
                    print("LoRa: Released database lock due to error in ACK handling")
                except:
                    pass
                self.waiting_for_ack = False
                self.pending_record = None
                self.pending_sample_num = None
    
    def stop_communication(self):
        """Stop communication and cleanup"""
        print("LoRa: Stopping communication...")
        self.running = False
        
        # Release any held database lock
        if self.waiting_for_ack and self.database_lock.locked():
            try:
                self.database_lock.release()
                print("LoRa: Released database lock on shutdown")
            except:
                pass
        
        # Close serial connection
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                print(f"LoRa: Closed serial port {self.port}")
            except:
                pass
        
        # Print statistics
        print(f"LoRa: Communication stopped. Stats - Sent: {self.records_sent}, ACKs: {self.acks_received}, Timeouts: {self.timeouts}")
    
    def get_status(self):
        """Get current status of comms and statistics."""
        return {
            'running': self.running,
            'waiting_for_ack': self.waiting_for_ack,
            'pending_sample_num': self.pending_sample_num,
            'records_sent': self.records_sent,
            'acks_received': self.acks_received,
            'timeouts': self.timeouts
        }