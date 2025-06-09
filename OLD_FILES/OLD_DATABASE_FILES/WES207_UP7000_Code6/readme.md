# RTT Tower Code READ ME
Note: This file assumes you already have a high level understanding of the RTT project.

## 1. High Level Overview

This code should be installed on each Tower. The tower number and the database name will be updated in towerConfig.py and is further discussed in Section 2.

This code will generate fake data & feed it into the database (.db file) using SQLite3. A python handler (runme.py) will have a daemon thread for generating data & then storing in the database. A different thread will send data to the Heltec V3 (LoRa board) via serial so data can be sent to the GCS. The Heltec will then send a command to the handler (via serial) to either: 1) delete the entry from the database if the GCS sends an acknowledged message or 2) let the handler know that the message failed and the entry will need to be resent.


## 2. Usage and Code Maintenance

### 2.1 How to Use this Repo

Clone the repo (either download to your computer or clone using ssh). In VSCode, run the file "runme.py" in a python dedicated terminal. Otherwise, open a new terminal, change to the directory the file is located ($cd "path") and run runme.py using "$python3 runme.py".

If you would like to "reset" the database, you can delete the .db file (likely named TowerX_data.db). The code will automatically make a new database if no database with the designated name exists.

Once running runme.py, it will print the current database (everything that has not yet been sent). It will then begin generating new data and attempting to send data from this Tower to the GCS.

Ensure that you call the TowerDatabase object using object.add_record(record) where record is an array with the packet structure defined in section 2.3. 

### 2.2 Updating the Code
Read Section 3 (File Descriptions) prior to making any adjustments to the code. File dependencies and an in depth overview of each file are described here.

Currently, the code generates data by making a generator class object in "runme.py" and targets the "gen_thread_target()" method.

Ensure you follow the packet format in Section 2.3 and create a way to increment sample number (starting index at 1).

Note: there is no logic to distringuish if a device is seen by multiple Towers at the same time. There will be multiple (likely different) samples created and stored in the GCS with this.

### 2.3 Packet & Database Structure
The packet will consist of the following information. It is stored in the database in this order and using the the variables names (database columns) in parentheses below:
1. Tower Index Number (tower_id)
2. Device Number (database.DEVICE_IDX) #note that it will take the number from towerConfig directly so you don't need to pass this value.
3. Sample Number (sample num)
4. Time Stamp (time_stamp)
5. Latitude (latitude)
6. Longitude (longitude)
7. Altitude (altitude)


## 3. File Descriptions
Below is a breakdown of all files within this section of the repo.

### 3.1 runme.py
This is the main file you will actually run. There are two threads created
1. To generate data & insert that data into the databse.
2. To send data to the Heltec for LoRa transmission. Once acknowledged, it will delete the entry (entries) from the database. If no ack, it will not delete the entry.

These threads use mutex locks [_lock = threading.Lock] to ensure only one thread can access the database at a time. Thread1 will use non-blocking aquire to access the database so that it will still generate data in the event it cannot access the database. This data will be stored in a temporary array and added to the database when it next gains access. Thread2 will use blocking acquire so that it can send data as soon as it receives the ability to access the database. 

### 3.2 database.py
This file is where the database is created and manipulated using the class object TowerDatabase.
When sending data from the database to the LoRa board, you must format the record into a comma delineated string using _record_to_string(). Both methods print_row() and print_first_row() will return the record in this format for you.

Upon initializing, it will have the following attributes:
1. db_name (name of the database from towerConfig.py)
2. _initialize_db() (a private method call to initialize the database if it does not already exist)
3. self.sample_counter: This keeps track of the number of the next generated sample. It is stored in a json file.

This class has the following methods:
1. _initialize_db(): initialize the database. Never call this method, it will be automatically called when the object is created.
2. add_record(records): adds a record to the database, where record is an array input that will have the same packet structure defined in Section 2.3.
3. delete_ack(sample_nums): Delete record(s) from the database, where sample_nums is the index of the sample(s) to be deleted.
4. print_table_header(): Print the table header for debugging & terminal output only
5. print_database(): This will print the entire database.
6. get_next_sample_num(): This will return the next sample index. This is for inserting the sample into the database and is stored in json file in case the database is every empty since all records were sent (because then it'll reset the sample num to 0 or 1).
7. print_row(print_row): Will print a specific row from database, where print_row is the sample_num you would like to print. Also returns that record.
8. print_first_row(): returns the first row from database (if it exists).
9. __record_to_string(record): returns the input record vector as a comma delineated string. Needs to be in this form to send over LoRa.
9. _save_config(): Save the current sample counter. Can add more in future if desired.
10. _load_config(): Load the current sample counter. Can add more in future if desired.

Note: database index (sample_num) starts at 1 like Matlab, not zero! DEFAULT_SAMPLE_NUM is set to zero, but becomes 1 when first called.

### 3.3 towerConfig.py
This file is where the tower constants are kept. The tower number is stored as TOWER_ID and the database name is stored as DB_Name. Be sure to update these to the correct tower number prior to testing.

Additionally, the format for printing data to terminal output is stored here. Use "TowerDatabaseObject.print_table_header()" to print the header.

### 3.4 dataGen.py
This file is where the database is created and manipulated using the class object TowerDatabase. In final Tower implementation, this should not be included because real data will be fed to the database. You will need to copy the data structure and the way it stores data in the database. Most notably, it should copy the way gen_thread_target() and _data_generation_loop() use the locks. You should use **non-blocking** acquire when trying to enter data. If it has the lock, it should store the data in the database as normal. If it does not acquire the lock, it should just store it in a temporary array (temp_record). More data about this is in gen_thread_target()

Upon initializing, it will have the following attributes:
1. database = database.TowerDatabase() call database class
2. database.print_database() to print the database
3. sample_counter to index the next sample counter.
4. running = False to indicate when the file thread is running.
5. self.add_queue = False to indicate if there is a queue to be added to the database. This is only used if Thread1 in runme.py could not access the database when creating a sample, so it stores the record(s) in a temporary array to add to the database later. If True, then there is a backlog of data to be added to the database.

This class has the following methods:
1. _generate_data(device_id): This generates a single record for a specific device_id. Time is using iso standard and stripped into a more readable format. We generate a sample using a uniform curve that can vary but +/- .001 degrees and from 0-100 in altitude. Units for this don't matter, but you should be consistant. A record consists of towerConfig.TOWER_ID, device_id, self.sample_counter, timestamp_short, latitude longitude, & altitude. Make sure to accumulate the self.sample_counter too.
2. _data_generation_loop(_L): Lock is the argument passed to the method. This function detemines which devices were seen every COLLECTION_INTERVAL seconds, then loops through and generates data for those devices. Output "temp_record" is empty if it was able to write to database and has record(s) if it was not able to access the database. The generated data is printed for console output, but this is not required.
3. gen_thread_target(_L): This is the target of Thread1 from runme.py and is passed the lock. self.running is set = True before starting the Thread, and setting self.running to False will stop data generation. First, it checks if there is a queue of data that was generated but not yet stored in the database, then tries to acquire the lock to enter those records to the database also using **non-blocking** because it is okay if this queue gets large. If it does acquire the lock, then it enters those records to the database and sets self.add_queue to False to show that there is no longer a queue. We then generate record(s) and set to temp_record. If temp_record is empty, then no records were generated or the records were able to access the database. If temp_records is not empty, it will append the new record(s) to record_queue as a list and set self.add_queue to True to signal that there is a queue. At the end, the Tower sleeps for COLLECTION_INTERVAL (set to 1 second for now).


### 3.5 LoRaAttributes.py
Note: This file has **NOT** been incorporated to the full project and is a starting point for future implementation. You will likely need to translate this code into C/C++ and store in the SRAM on the Heltec board (rather than on the UP7000). A version similar to this file should be included in final Tower implementation because the LoRa communication parameters must remain persistent across restarts and must follow FCC compliance rules.

This file initializes, stores, and maintains the LoRa parameters using the class object LoRaAttributes. It initializes default values if no prior configuration is found and loads the previous configuration the JSON file LORA_CONFIG_FILE/lora_config.json. Most notably, this file ensures the dwell time does not exceed the legal maximum by verifying every parameter change against FCC rules. If the proposed change would exceed legal limits, it is not applied and the previous settings are restored.

Make sure you understand how many bytes are in each sent packet over air and set PAYLOAD_LENGTH_PER_PKT to that value. Right now we just have a placeholder value.

Upon initializing, it will have the following attributes and save them to the config file:
1. self.sf = SF_DEFAULT
2. self.channel = CHANNEL_DEFAULT
3. self.carrier_frequency = FREQ_DEFAULT
4. self.records_per_pkt = RECORDS_PER_PKT_DEFAULT
5. self.coding_rate = CODING_RATE_DEFAULT
6. self.bandwidth = BANDWIDTH_DEFAULT
7. self.preamble_len = PREAMBLE_LEN_DEFAULT
8. self.explicit_header = EXPLICIT_HEADER_DEFAULT
9. self.crc = CRC_DEFAULT
10. self.ldr_opt = LOW_DATA_RATE_DEFAULT
11. self.payload_len = PAYLOAD_LENGTH_PER_PKT     
12. self.dwell_time = self._calculate_dwell_time()

This class has the following methods:
1. _save_config(): Saves the current configuration to lora_config.json so it can be reloaded after power cycling.
2. _load_config(): Loads configuration from lora_config.json. If file is corrupted or missing values, it reverts to default.
3. _calculate_dwell_time(): Calculates the estimated LoRa dwell time based on current configuration. Uses symbol duration, preamble, payload length, coding rate, etc, but assumes LDR optimization is off. It would be best to double check my work before implementing since dwell time calculations are estimates.
4. _is_dwell_time_legal(): Compares the calculated dwell time to MAXIMUM_DWELL_TIME (400 ms). If the time is under this threshold it returns True, but returns False if not legal.
5. get_LoRa_attributes(): Returns a tuple of the current LoRa configuration but use __str__() if human-readable output is needed.
6. __str__(): Returns a formatted string with current configuration for console output.
7. set_sf(new_SF): Updates the spreading factor (between 7 and 10) and checks if dwell time is legal before saving.
8. set_channel(new_channel): Updates the LoRa channel and recalculates carrier frequency accordingly and checks if dwell time is legal before saving.
9. set_records_per_pkt(new_rec_per_pkt): Updates the number of records per transmission and checks if dwell time is legal before saving. Right now, we are only using 1 record for packet, but this would allow for more in the future.
10. set_coding_rate(new_cr): Updates the coding rate tuple and checks if dwell time is legal before saving.
11. set_bandwidth(new_bw): Updates bandwidth in kHz and checks if dwell time is legal before saving.
12. set_preamble_len(new_preamble_len): Updates preamble length in symbols and checks if dwell time is legal before saving.
13. set_explicit_header(new_EH): Updates explicit header flag and checks if dwell time is legal before saving.
14. set_crc(new_crc): Updates whether CRC is enabled or not and checks if dwell time is legal before saving.
15. set_ldr_opt(new_ldr_opt): Updates LDR optimization flag. This flag is currently ignored in dwell time calculations, but allows for it to be used in the future. It also checks if dwell time is legal before saving.
16. _set_payload_len(): Called by set_records_per_pkt() to update the payload length. Do not call this directly. PAYLOAD_LENGTH_PER_PKT is used in this and must be the correct length (in bytes) for the calculation/estimate to be accurate.


## 4. Suggested Improvements
This section contains improvements that could be made to the code to further optimize the code or allow for additional functionality.

### 4.1 Adding Records to Database
The database currently adds the record(s) to the database one at a time. You could optimize this to use "execute many" to add multiple records at the same time rather than one record at a time if many records will be added at a time.

### 4.2 Implement LoRaAttrubutes to the System
As described above, LoRaAttributes is a working sample file but has not yet been integrated into the system as a whole. Implementing this onto the Heltec board's SRAM (or similar) would be ideal, likely as C/C++ code for speed.

### 4.3 Optimize Packet Structure
We kept the packet structure basic so as you can easily update it in the future and in case it does not work properly. This allows you to add more parameters to be sent from the Tower to GCS if you desire (e.g. temperature). To optimize, you can adjust the MAC layer to be only the number of bits required per data type sent and send data in bits. This would increase throughput since only meaningful data would be sent. For example, you likely only need 8 digits (5 or fewer digits after decimal) for lat/long since 1.1m precision probably beats the accuracy of the system as a whole. This would only require ~25/26 bits of info, which is less than the 32 bits in a float. This can be similarly optimized for altitude and other data types sent.

