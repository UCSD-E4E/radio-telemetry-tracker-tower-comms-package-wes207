#database.py
#This is for creating and maintaining the database.
import time
import sqlite3
import towerConfig

#Indexes for the records be added to the database.
TOWER_IDX       =   0   #int        Tower is always same as from towerConfig.py
DEVICE_IDX      =   1   #int        Device number on animal
SAMPLE_IDX      =   2   #int        Sample number
TIME_IDX        =   3   #str        timestamp index
LAT_IDX         =   4   #float      Lat index
LON_IDX         =   5   #float      Lon index
ALT_IDX         =   6   #float      Alt index


#create db of random latitude, longitude, etc.
#all data will be from tower 1
class TowerDatabase:
    #attributes of database
    def __init__(self, db_name =towerConfig.DB_Name):
        self.db_name = db_name
        self._initialize_db() #initialize the database once started

    # METHODS in class:
    # 1) initialize the db (internal use only), 2) add a new data record, 3) delete ack'd records
    # 4) print table header 5) print the current database 6) get most recent sample index 7) print specific row


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
    def add_record(self,record):
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
        return record_id
    
    #3 Deleted record(s) that have been acknowledged
    def delete_ack(self, sample_nums):
        #sample_nums is a vector with row ID's of all records that have been acknowledged
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()

        if not sample_nums:
            return 0 #exit early if nothing was acknowledged
        
        #Delete from the database here
        placeholders = ','.join('?' for _ in sample_nums) #eg (?,?,?) if sample_nums is len(3)
        query = f'''
            DELETE FROM records 
            WHERE sample_num IN ({placeholders})
        '''

        cur.execute(query, sample_nums) #make the change
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

    #6 Get the most recent sample from db
    def get_last_sample_num(self):
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        
        cur.execute('SELECT MAX(sample_num) FROM records')
        result = cur.fetchone()[0]
        
        con.close()
        return int(result) if result is not None else 0
    
    #7 Print specific row from db
    def print_row(self,print_row):
        con = sqlite3.connect(self.db_name)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        query = 'SELECT * FROM records WHERE sample_num = ?'
        cur.execute(query, (print_row,))
        row = cur.fetchone()

        #print if entry exists
        if row:
            print(f"\nDatabase entry {print_row}:")
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
            print(towerConfig.ROW_FORMAT.format(*record)) # the "*" is unpacking operator, not pointer.
        else:
            print(f"\nNo entry found with sample_num = {print_row}.\n")
            return 0
        
        con.close()
        return record
        
