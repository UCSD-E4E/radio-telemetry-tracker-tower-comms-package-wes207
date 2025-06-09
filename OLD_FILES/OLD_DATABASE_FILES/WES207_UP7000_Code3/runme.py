#dataGen.py
#This file is the handler that generates data & enters it into the database.
# To Do: Update Thread2 to run interface between database and Heltec. Use lock (_L) to access database.


import towerConfig
import database
import dataGen
import threading
import time
import numpy as np

threads = [] #empty array for the threads

if __name__ == "__main__":
    #print("Data Generator running. Press Ctrl+C to stop.")
    generator = dataGen.DataGenerator()
    print("\nAbout to start data Generator.\nPress Ctrl+C to stop.")
    
    try:
        # Run for a minute to test
        #print("Data Generator running. Press Ctrl+C to stop.")
        '''Loop through and generate data for all devices that are within range.'''
        
        generator.print_table_header() # Print table header
        
        _lock = threading.Lock() #Lock is so only one member can access database at a time.
        #need daemon to end the thread with keyboard interrupt
        #Use nonblocking and blocking intelligently depending if we want program to wait or not.

        #loop thru data gen. Uses non-blocking lock.
        thread1 = threading.Thread(target=generator.gen_thread_target, args=(_lock,), daemon=True) 
        threads.append(thread1) #creates the new thread number
        generator.running = True

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #To Do: Add code to send data. Using BLOCKING! we will wait for lock to be available.
        #thread2 = threading.Thread(target=sendData, args=(_lock,), daemon=True)
        #threads.append(thread2) #creates the new thread number
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        #loop thru data gen. Uses non-blocking lock.
        thread3 = threading.Thread(target=generator.del_thread_target, args=(_lock,), daemon=True)
        threads.append(thread3) #creates the new thread number

        thread1.start() #Generate data & add to database
        #thread2.start() #Will add code to send data & mark ack
        thread3.start() #Delete data every X seconds.

        #sleep so you can catch keyboard interrupt & have time to close threads.
        while True:
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\nStopping data generator...")
        generator.running = False #stop thread loops!
        #TO DO: add logic/attribut/etc to let LoRa know to stop looping

    finally:
        thread1.join()
        #thread2.join()
        thread3.join()
        print("Threading completed.\n")