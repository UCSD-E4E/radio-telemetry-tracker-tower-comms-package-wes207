#database.py
#This is for creating and maintaining the database.
import time
import datetime
import sqlite3
import towerConfig
import os
import json

#Indexes for the records be added to the database.
TOWER_IDX       =   0   #int        Tower is always same as from towerConfig.py
DEVICE_IDX      =   1   #int        Device number on animal
SAMPLE_IDX      =   2   #int        Sample number
TIME_IDX        =   3   #str        timestamp index
LAT_IDX         =   4   #float      Lat index
LON_IDX         =   5   #float      Lon index
ALT_IDX         =   6   #float      Alt index

DEFAULT_SAMPLE_NUM          =   0                           #Default if no samples collected yet.
SAMPLE_NUM_CONFIG_FILE      =   "sample_num_config.json"    #config file to store sample number value in case backlog cleared.


#create db of random latitude, longitude, etc.
#all data will be from tower 1
class TowerDatabase:
    #attributes of database
    def __init__(self, db_name =towerConfig.DB_Name):
        self.db_name = db_name
        self._initialize_db() #initialize the database once started
        self.sample_counter = self.get_next_sample_num("boot") #entry number for this newly generated data
        

    # METHODS in class:
    # 1) initialize the db (internal use only), 2) add a new data record, 3) delete ack'd records
    # 4) print table header 5) print the current database 6) get next sample index 7) print specific row
    # 8) return first record in the database 9) save current sample idx to config json, 10) load current sample idx from config json


    #1 Initialize db if doesn't exist
    def _initialize_db(self):
        #Create database and tables
        #ref 1:     https://docs.python.org/3/library/sqlite3.html
        #ref 2:     https://sqlite.org/lang_createtable.html

        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS records (
                    tower_id INTEGER NOT NULL, 
                    device_id TEXT NOT NULL,
                    sample_num INTEGER NOT NULL,
                    time_stamp TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL NOT NULL                  
        )''')
            #id INTEGER PRIMARY KEY AUTOINCREMENT # I don't think we need, but may need to add to table
                #https://sqlite.org/autoinc.html
                #https://stackoverflow.com/questions/7905859/is-there-auto-increment-in-sqlite
        con.commit()
        con.close()
    
    #2 To add a record to the database
    def add_record(self,record,print_log=None):
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        #To Do: maybe optimize to "execute many" if many records being added at once or see poor performance.
        cur.execute('''INSERT INTO records 
                    (tower_id, device_id, sample_num, time_stamp, latitude, longitude, altitude) 
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        int(towerConfig.TOWER_ID), #Could use: "record[TOWER_IDX]," instead
                        #int(record[TOWER_IDX]),
                        int(record[DEVICE_IDX]),
                        int(record[SAMPLE_IDX]),
                        str(record[TIME_IDX]),
                        float(record[LAT_IDX]),
                        float(record[LON_IDX]),
                        float(record[ALT_IDX]),
                    ))
            #INSERT INTO people (first_name, last_name) VALUES ("John", "Smith");
            # https://www.sqlitetutorial.net/sqlite-python/insert/
        record_id = cur.lastrowid
        con.commit()
        con.close()
        if print_log:
            print(f"Added record with sample number #{record[SAMPLE_IDX]} to database. \n")
        return record_id
    
    #3 Deleted record(s) that have been acknowledged
    def delete_ack(self, sample_num):
        #sample_nums is an int with row ID of record that have been acknowledged & is ready to delete
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()

        if not sample_num:
            return 0 #exit early if nothing was acknowledged
        
        #Delete from the database here
        query = f'''
            DELETE FROM records 
            WHERE sample_num = ?
        '''
        cur.execute(query, (sample_num,)) #Use "(sample_num,)" because cur.execute expects sample_num as a tuple since "?" is placeholder
        deleted_count = cur.rowcount
        print(f"Deleted {deleted_count} records from Tower {towerConfig.TOWER_ID} database.")
        con.commit()
        con.close()

        return deleted_count

    #4 print the table header
    def print_table_header(self):
        print("\n" + towerConfig.TABLE_HEADER.format(*towerConfig.COLUMN_NAMES) + "\n" +(towerConfig.DIVIDER_LINE)) #print table header
        
    #5 Output entire database (for debugging only)
    def print_database(self):
        print("\nPrinting current database:\n")
        con = sqlite3.connect(self.db_name)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM records ORDER BY sample_num")
        rows = cur.fetchall()

        #Print table header and the records row by row
        self.print_table_header()
        for row in rows:
            print(towerConfig.ROW_FORMAT.format(
                row["sample_num"],
                row["tower_id"],
                row["device_id"],
                row["time_stamp"],
                row["latitude"],
                row["longitude"],
                row["altitude"],
            ))
        con.close()

    #6 Get the most recent sample from json file. NOT from DB in case is deleted locally or emptied (all records sent).
    def get_next_sample_num(self, mode=None):
        if os.path.exists(SAMPLE_NUM_CONFIG_FILE):
            self._load_config()
            if mode != "boot":
                self.sample_counter += 1
                #increment except when datagenerator object created.
        else:
            self.sample_counter = DEFAULT_SAMPLE_NUM
        self._save_config()
        result = self.sample_counter
        return int(result) if result is not None else 0

    
    #7 Print specific row from db
    def print_sample(self,print_row):
        '''print a specific row as a string (comma delineated) and the sample number'''
        con = sqlite3.connect(self.db_name)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        query = 'SELECT sample_num, tower_id, device_id, time_stamp, latitude, longitude, altitude FROM records WHERE sample_num = ?'
        cur.execute(query, (print_row,))
        row = cur.fetchone()

        #print if entry exists
        if row:
            print(f"Sample Number {print_row}:")
            self.print_table_header()
            #save output in array
            record = [
                row["sample_num"],
                row["tower_id"],
                row["device_id"],
                row["time_stamp"],
                row["latitude"],
                row["longitude"],
                row["altitude"],
                ]
            return_sample_num = row["sample_num"]
            print(towerConfig.ROW_FORMAT.format(*record)) # the "*" is unpacking operator, not pointer.
            con.close()
            record_string = self._record_to_string(record) #convert record to string for sending.
            return record_string, return_sample_num 
        else:
            print(f"\nNo entry found with sample_num = {print_row}.\n")
            con.close()
            return None, 0
        
    
    #8 return first row from db
    def print_first_row(self):
        '''print the first row as a string (comma delineated) and the sample number'''
        con = sqlite3.connect(self.db_name)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        query = 'SELECT sample_num, tower_id, device_id, time_stamp, latitude, longitude, altitude FROM records LIMIT 1'
        cur.execute(query, )
        row = cur.fetchone()

        #print if entry exists
        if row:
            print(f"First database entry:")
            self.print_table_header()
            record = [row["sample_num"], row["tower_id"], row["device_id"], row["time_stamp"], row["latitude"], row["longitude"], row["altitude"],]
            return_sample_num = row["sample_num"]
            print(towerConfig.ROW_FORMAT.format(*record)) # the "*" is unpacking operator, not pointer.
            con.close()
            record_string = self._record_to_string(record)
            return record_string, return_sample_num
        else:
            print(f"\nNo entry found in database\n")
            con.close()
            return None, 0
    
    #9 return last row from db
    def print_last_row(self):
        '''print the last row as a string (comma delineated) and the sample number'''
        con = sqlite3.connect(self.db_name)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        query = 'SELECT sample_num, tower_id, device_id, time_stamp, latitude, longitude, altitude FROM records ORDER BY sample_num DESC LIMIT 1'
        cur.execute(query, )
        row = cur.fetchone()

        #print if entry exists
        if row:
            print(f"Most Recent database entry (by sample number):")
            self.print_table_header()
            record = [row["sample_num"], row["tower_id"], row["device_id"], row["time_stamp"], row["latitude"], row["longitude"], row["altitude"],]
            return_sample_num = row["sample_num"]
            print(towerConfig.ROW_FORMAT.format(*record)) # the "*" is unpacking operator, not pointer.
            con.close()
            record_string = self._record_to_string(record)
            return record_string, return_sample_num
        else:
            print(f"\nNo entry found in database\n")
            con.close()
            return None, 0
        
    
    #10 Convert a record to string
    def _record_to_string(self,record):
        '''Return a record as a comma deliniated string. Input is as an array. Needs to be the new format to send over LoRa.'''
        # int       ,int     ,int      ,str       , flt (7), flt (7) ,flt (2)
        # eg 1,2,34,2025-04-20 16:55:12,12.1234567,123.123456,12.98
        record_string = "{},{},{},{},{:.7f},{:.7f},{:.2f}".format(
            record[0],  # sample_num (int)
            record[1],  # tower_id (int)
            record[2],  # device_id (int)
            #record[3],  # time_stamp (str)
            record[3].strftime("%Y-%m-%d %H:%M:%S") if isinstance(record[3], datetime.datetime) else record[3],
            record[4],  # latitude (float, 7 decimals)
            record[5],  # longitude (float, 7 decimals)
            record[6]   # altitude (float, 2 decimals)
        )
        return record_string

    #10/11 Save and Load most recent Sample Number in json file to persist between power cycling and database emptying.
    def _save_config(self):
        '''save current Sample Number as a dictionary to LORA_CONFIG_FILE.json'''
        config = {"Sample_Counter": self.sample_counter}
        with open(SAMPLE_NUM_CONFIG_FILE, "w") as file:
            json.dump(config, file)
    def _load_config(self):
        '''Load previous LoRa config if exists. If not exist, load initial values.'''
        #Note: Values should always exist, but get() allows to default back to original if file is corrupted upon power cycling. Resets to first sample though...
        with open(SAMPLE_NUM_CONFIG_FILE, "r") as file:
            config = json.load(file)
            self.sample_counter = config.get("Sample_Counter", DEFAULT_SAMPLE_NUM)



