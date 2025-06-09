#runme.py
#This file is the handler that generates data & enters it into the database.
# For future, you should replace Thread1 with the file that will add data to the database. Refer to sampleDBInterface.py for example.


import towerConfig, database, pyTower
import dataGen
import threading
import time
import numpy as np
import serial, random

threads = [] #empty array for the threads


if __name__ == "__main__":
    #print("Data Generator running. Press Ctrl+C to stop.")
    generator = dataGen.DataGenerator()
    print("\nAbout to start data Generator.\nPress Ctrl+C to stop.")
    
    try:
        # Run for a minute to test
        #print("Data Generator running. Press Ctrl+C to stop.")
        '''Loop through and generate data for all devices that are within range.'''
        
        _lock = threading.Lock() #Lock is so only one member can access database at a time.
        #need daemon to end the thread with keyboard interrupt
        #Use nonblocking and blocking intelligently depending if we want program to wait or not.

        #loop thru data gen. Uses non-blocking lock.
        thread1 = threading.Thread(target=generator.gen_thread_target, args=(_lock,), daemon=True) 
        threads.append(thread1) #creates the new thread number
        generator.running = True

        #Thread for the serial communication. 
        lora_comm = pyTower.LoRaCommunicator(_lock)
        thread2 = threading.Thread(target=lora_comm.start_communication, daemon=True)
        threads.append(thread2) #creates the new thread number

        thread1.start() #Generate data & add to database
        thread2.start() #Will add code to send data & mark ack


        #sleep so you can catch keyboard interrupt & have time to close threads.
        while True:
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\nStopping data generator...")
        generator.running = False #stop thread loops!
        #TO DO: add logic/attribut/etc to let LoRa know to stop looping
        if 'lora_comm' in locals():
            lora_comm.stop_communication()

    finally:
        thread1.join()
        thread2.join()
        print("Threading completed.\n")