#dataGen.py
#This will generate bogus data every second that we will need to send
import time
import datetime
import random
import threading
import os
import numpy as np
import json

import towerConfig
import database

#Constants for generating data
NUM_DEVICES             =   20          #Number of devices deployed
LAT                     =   32.8812     #latitude
LON                     =   117.2344    #longitude
ALT                     =   0           #altitude (assume sea level)
PROB_DEVICE_SEEN        =   .05         #probability a device transmits to a tower. Arbitrary
COLLECTION_INTERVAL     =   1           #[seconds] how often data is collected


#create data and store into database
class DataGenerator:
    def __init__(self):
        self.database = database.TowerDatabase() #call database class
        #Print db contents:
        self.database.print_database()
        self.running = False
        self.add_queue = False

    # Generate a single record
    def _generate_data(self,device_id):
        '''Actually generate data here'''
        current_time = datetime.datetime.now().isoformat()
        #format timestamp from YYYY-MM-DDTHH:MM:SS.ssssss to readable YYYY-MM-DD HH:MM:SS
        timestamp_short = current_time.split("T")[0] + " " + current_time.split("T")[1][:8]

        latitude = LAT + random.uniform(-0.001, 0.001)
        longitude = LON + random.uniform(-0.001, 0.001)
        altitude = ALT + random.uniform(0, 100)

        record = np.array([
            towerConfig.TOWER_ID,
            device_id,
            self.database.get_next_sample_num(),
            timestamp_short,
            latitude,
            longitude,
            altitude
        ])
        return record
    
    def _data_generation_loop(self,_L):
        '''Detemine which devices were seen. Then loop through and generate data for those devices. check "if record" to see if empty. 
           If record==true, did not enter the record(s) into the database successfully & need to attempt later.'''
        dev_active = np.random.binomial(n=1, p=PROB_DEVICE_SEEN, size=NUM_DEVICES)

        #If none seen, leave early
        popcount = np.count_nonzero(dev_active) #number of devices seen
        if popcount == 0:
            return [] #empty array b.c. we input into database.

        temp_record = [] #in case can't access db
        #If cannot access to database w/ lock, we will just store as temp and try again later!
        can_access_DB = _L.acquire(False) #"False" = NON blocking!
        if not can_access_DB :
            #initialize temp array to store generated data in if we cannot access database. 8 is length of a record.
            #temp_record = np.zeros((popcount,8))
            temp_record = [] #List might be better.
            accum = 0 #accumulator to know which row of temp_record to add data to

        for i in range(NUM_DEVICES):
            if dev_active[i] == 1: #only send data if device was seen
                record = self._generate_data(i) #generate the data

                if can_access_DB == True:
                    self.database.add_record(record)
                    print(towerConfig.ROW_FORMAT.format(
                        int(record[database.SAMPLE_IDX]),
                        int(record[database.TOWER_IDX]),
                        int(record[database.DEVICE_IDX]),
                        str(record[database.TIME_IDX]), 
                        float(record[database.LAT_IDX]),
                        float(record[database.LON_IDX]),
                        float(record[database.ALT_IDX]),
                    ))
                else: #if can't access database with lock, then store as temp array and return it. We will try again later.
                    temp_record[accum,:] = record
                    accum += 1
        
        _L.release() #release lock!
        return temp_record
    

    def gen_thread_target(self, _L):
        record_queue = [] #Initially nothing in queue to be added to database
        #self.database.print_row(1) #in case you want to print a specific row from the database

        print("\nNewly generated data added to database:")
        self.database.print_table_header()
        while self.running:

            #If queue, try to clear the queue first
            if self.add_queue == True:
                can_access_db = _L.acquire(False) #non-blocking acquire
                if can_access_db:
                    for row in record_queue:
                        self.database.add_record(row) #add records one at a time.
                    record_queue = [] #zero the queue
                    self.add_queue = False
                    _L.release()
            
            #Generate new data.
            temp_output = self._data_generation_loop(_L)

            if temp_output: #may need to fix if get errors, need to check.
                for row in temp_output:
                    record_queue.append(row.tolist()) #needs to be list for performance and to add to database (using SQLITE3)
                self.add_queue = True
            temp_output = [] #re-zero so won't cause errors in future. This may cause error, so can remove while debugging or try temp_output = 0
            time.sleep(COLLECTION_INTERVAL)

    


