#SAMPLE instructions to interface with database.py
#                                                         
# Make sure to run the "runme.py" file before running this. You need the database to have data for this to work.
    #If you want to reset the database since you manually manipulate the database file:
        # DELETE THE "towerX_data.db" and "sample_num_config.json" files.
            # These files will auto create if they don't exist next time you
        #Re-run the "runme.py" file for a bit to input a number of records into the database after deleting the files.


import towerConfig                      #.py file
import database                         #.py file
import numpy as np                      #Input an array to the database
import random                           #Not needed for real data.
from datetime import datetime           #For timestamp


# SETUP: create object for manupulating the database. "db" will be the object.
db = database.TowerDatabase() #call database class
db.print_database() #print current database
#Note: This prints the databse in order of sample number, not by timestamp!


#Test 1
print("\n\n\nTest 1: print first row, delete first sample, then reprint first row to show it deleted. Should show incremented. \n")
record1,samp1 = db.print_first_row()
print("record:", record1, "sample:", samp1, "\n")

sample_num_to_delete = samp1 #the sample number from the first row
db.delete_ack(sample_num_to_delete) #I ignore the return of how many row(s) were deleted. Should be one.

record1,samp1 = db.print_first_row()
print("record:", record1, "sample:", samp1, "\n\n\n")



#Test 2: 
print("\nTest 2: Print a specific row (debugging only, usually you should just call for the first row!) \n")
sample_to_print = 10
record2,samp2 = db.print_sample(sample_to_print)
print("record:", record2, "sample:", samp2, "\n") #This is what you receive as string comma delineated
print("\n\n\n")


#Test 3: 
print("Test 3: Add a (pseudo-random) record. Then get the record number (since it's the most recently added record). Then print that record.\n")
_, new_record_num = db.print_last_row()
new_record_num += 1
print("\n")
current_time = datetime.now()
formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
record_to_add = np.array([
            towerConfig.TOWER_ID,               #Tower number (always from config file, be sure to update to match Tower Number)
            random.randint(0, 19),              #Device ID
            new_record_num,                     #sample num. I used "self.database.get_next_sample_num()" in dataGen file
            formatted_time,                     #Timestamp & format e.g. 2025-05-18 16:12:42
            32.8812,                            #Lattitude, constant for example
            117.2344,                           #Longitude, constant for example
            20                                  #Altitude, constant for example
        ])
print_log = True #I want to print the sample we added to the database to show we correctly called the method and added the record.
db.add_record(record_to_add,print_log)
added_record, added_record_num = db.print_last_row() #Use this in debug only, shouldn't really be used in production...
#record_check,samp_check = db.print_row(added_record_num) #another way to check!
print("record:", added_record, "\t Sample:", added_record_num, "\n\n\n")
#Note: Should always increment a counter in a json/config file to keep track of sample number (keep track on bootup), but we can pick a random number here.



# Now print the database again
db.print_database() #print current database
#Note: This prints the databse in order of sample number, not by timestamp!