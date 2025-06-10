# WES207
Ricardo Lizarraga, William Gong & Connors Jackson

# RTT Capstone Project

See individual folders for more detailed readme's and inline documentation.

## Folder Structure

### MVP 1

This folder is the first fully integrated code that will send data from the Tower to the GCS. You need to run "pyTower.py" on the tower and it will look at the terminal output from the database file, then send that to the GCS. This is an obsolete version because it does NOT access the database directly and only looks for terminal output! This means records are not deleted, but it will still access/accum/send the next record (through terminal output) once an "ack" is received.

### MVP 2.0

This is the first version which accesses the database and will delete records when an "ack" is received from the GCS. This version is obsolete because a large bug is in the code: the first record in the database will be deleted regardless of what type of "ack" is receieved. This means if the GCS requests the RSSI and responds with an "ack" to show that the RSSI was received, then the first record in the database will be deleted. We only want the record to be deleted from the database if the "ack" is from the "rec?" request.

This version also sends records continuously which is not desired. This is patched in the next version.

### MVP 2.1

This is the most up to date and functional product.


### Old Versions (version controlled)

#### Original MVP: This would be MVP0.

LoRa_GUI_1 is the MVP for the project. More documentation is provided inline and with readme's in the directory, but further documentation will be provided once merged with the database with the final product. There are 4 main files currently:
1. GCS python GUI
2. GCS Heltec V3 LoRa Board C++ code
3. Tower Heltec V3 LoRa Board C++ code
4. Tower UP7000 Python code
This does not currently provide a way to input data from elsewhere, but it provides a method of sending (randomly generated) data from a Tower to the GCS.

#### GCS and TOWER

These files are only here for version control and are probably not useful for other students. Tower directory is the LoRa code to be run on the Tower and needed to be merged completely with the UP7000 directory code. It is the interface between the MVP and the database but needs to be updated since it was more proof of concept. GCS directory is the code to be run on the GCS. This is out of date and obsolete. 

#### OLD_DATABASE_FILES

The OLD_DATABASE_FILES are the older versions of the database files where data is created and stored locally on the tower.


## Setting Up the System

### Hardware

USB-C cables are required for the Heltec boards (for power and SPI/UART serial communication). You will need a mouse/ethernet cable/monitor/keyboard/HDMI for the UP7000 to use it, along with a USB drive to flash the Up7000 with Ubuntu. The following are required for the system.

1. ESP32 LoRa V3: https://www.amazon.com/dp/B0DP6FJK69?ref=cm_sw_r_cso_cp_apan_dp_4D1XD880WVHX8VXAH5S5&ref_=cm_sw_r_cso_cp_apan_dp_4D1XD880WVHX8VXAH5S5&social_share=cm_sw_r_cso_cp_apan_dp_4D1XD880WVHX8VXAH5S5&th=1
2. UP-ADLN100-A10-0432 (Up7000 w/ Ubuntu, 8GB Memory, 64GB eMMC): https://up-shop.org/default/up-7000-series.html 
3. EP-PS12V5A60WFJ (12V@5A Power Supply): https://up-shop.org/default/up-core-plus-power-supply-12vat5a.html
4. EP-CBPC125V3PUS (US Type Power Cord Plug 1800±30mm): https://up-shop.org/default/power-cord-u-s-plug.html

### Software

More detail is also in individual readme's within the "MVP" folders.

On the Tower, ensure the following are installed. You may need to connect to your router (via ethernet) to get internet since the UP7000 does NOT come with a WiFi chip.
1. Ubuntu: We tested with Ubuntu Desktop 22.04: https://releases.ubuntu.com/jammy/
2. Python/Python3
    2a. $ sudo apt install python3-pip
3. Install the following: PyQt5 pyserial numpy
    3a. $ pip install PyQt5 pyserial numpy
4. Ensure usb to serial driver is set up to connect with Heltec V3 for Windows. Silicon labs CP210x VCP driver should work: https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads

For your computer you develop from and the GCS, you should have the following installed:
1. Everything listed as required for the Towers.
2. Install VSCode.
3. Install the PlatformIO extension for VSCode. Professor Pat Pannuto has a great explanation for how to set up and flash devices using PlatformIO. We will try to summarize his explanation, but will copy/paste from it as well. Original link here: https://docs.google.com/document/d/1Z9RdAXe5OVurrq5v1Pm4KPiI-Q36jmKx4vZe1AOKdGU/edit?tab=t.0 
    3a. Install the PlatformIO extension: https://platformio.org/install/ide?install=vscode
    3b. This should take ~2 minutes maximum. When it’s done, you’ll have to reload VSCode and the little Ant icon will appear on the left side of it. Make sure you have Python and venv/virtualenv installed and available on your path. Click open to get yourself to the PlatformIO homepage.
    3c. This is the extension you MUST use to flash the programs to the Heltec V3 LoRa boards (tower.cpp and gcs.cpp)
    3d. Use the “Open Project” button on the PlatformIO homepage to open one of the folders within your group’s Github starter repo. The best one to start with is “blink-and-print”. This may take 5-10 minutes the first time you do this.
    3e. In PlatformIO, click “Upload and Monitor” to compile and flash the application and then automatically open a serial port to it.
    3f. See pages 6-7 for additional troubleshooting if you encounter any errors.
        The LoRa lab also has good information: https://docs.google.com/document/d/1kqiE1Ym0D8WL9KlhcqM9wjnr8Qx-XWKhpiIqEDAP7aY/edit?tab=t.0 

You will also need to configure the Tower Number. We did this for you, but you can do this in MVP_2.1/TowerX/towerConfig.py by updating TOWER_ID and DB_Name to the correct numbers. This is required so when data is sent to the GCS it will come showcase the correct tower number. This needs to be updated while setting up the tower.

You will need to set up the correct COM port for serial communication on the Towers and the GCS.
1. Tower: Go to pyTower.py and update the correct line of code (below). Only use one depending on the OS you are running the file from and keep the other 2 commented out.
        #self.port = 'COM5'                             # Serial port (windows), use device manager to find the correct port and change port to "COMXX"
        #self.port = '/dev/ttyUSB0'                     # Serial port on Ubuntu. Find correct port using $ls /dev/tty* 
        #self.port = '/dev/tty.usbserial-2'             # Serial port for mac setup. Find correct port.
2. GCS: Go to gcs.py and update the correct line of code (below).
        #port = 'COM3'                              # Serial port (windows), use device manager to change port to COMXX
        #port = '/dev/tty.usbserial-0001'          # Serial Port for mac
        #port = '/dev/ttyUSB0'                     # Serial port on Ubuntu. $ls /dev/tty* 
        #port = '/dev/tty.usbserial-2'             # Serial port for mac

For Rotation mode, you need to update the variable "max_tower" in gcs.py to the number of Towers in the system. For example, if you have 3 towers set up, you should put max_tower = 3.

You will also need to update thread1 in "runme.py" to target your database generator file. Currently it is set to a random generator file. Your file should make an object to manipulate the database; see sampleDBInterface.py for an example of how to manipulate the database (add data, delete data, print the database, etc.). Your file must use the lock "_lock" to access the database to ensure only thread1 or thread2 will access the databse at a time. I suggest using non-blocking acquire. See my implementation in dataGen.py gen_thread_target(self, _L) for how I handled this. If I could not acquire the lock, I stored the data in a temporary list and input into the database the next time I could access the database. I used this method so that Thread2 (for sending data to the GCS) could access the database more often (using blocking acquire), but you can use blocking acquire on Thread1 if you'd like.

You should delete current database (towerX_data.db) and the sample number accumulator (sample_num_config.json) files when setting up the tower for deployment. The program will auto create these files and set the next sample to '1' if it does not exist.

#### Update Channel, Spreading Factor, and Bandwidth

To Update Channel (Center Frequency):
1) GCS: update the variables CHANNEL_DOWNLINK and CHANNEL_UPLINK in the file gcs.cpp
2) Tower: Update the variables CHANNEL_DOWNLINK and CHANNEL_UPLINK in the file tower.cpp

Use the function tune_to_channel(channel) to update the actual frequency in both files. You can use advance_channel() to advance to the next channel (up to channel 40). 


To update the Spreading Factor (SF):
Same as the channel number above but update JN_LORA_SPREAD .

To update the Bandwidth (BW):
Same as channel number and Spreading Factor with the variable JN_LORA_BW. **Note that the carrier frequencies you are allowed to use for 500kHz bandwidth are different than that of 125kHz.** The system is currently configured for 125kHz bandwidth transmissions. See Class 5 Update presentation Appendix for more information.

Future Improvements:
You can use the variables OTA.dl and OTA.ul in both files to store the variables locally. I recommend keeping this data local to the Heltec devices if you do try to add channel hopping. Either flashing a json file local to the device that stores the channel between device reboots (similar to how sample_num_config.json works) or using the OTA object would work. Look at LoRaAtributes.py (in tower) for some background of what you could do.

NOTE: You need to update tune_to_tx() and tune_to_rx() to send a non-static variable since they only use CHANNEL_DOWNLINK and CHANNEL_UPLINK.


#### Run The System

To run the system, you will run "runme.py" on the GCS and "gcs.py" on the GCS.

## GCS Python GUI

### Manual and Rotation Mode

You have the option to select the delays in receiving and transmitting. Use the "command" to select the type of command you'd like to send. Use "Auto/manual" to send to a specific Tower you have selected. Select "Rotation Mode" to rotate between all Towers in the system.

To update the number of Towers in rotation, update the variable max_tower in gcs.py. For example, max_tower=4 would rotate between 4 different towers.

### Run a Sequence

You can also use "Run a Sequence" to send a specific command to a Tower of your choice. You need to open "Sequence_Script_1.txt" and add the sequence you'd like to run. Each new line is a new command to be run. Be sure to save the file before running the sequence!

Command syntax:
    <Cmd>,<tower number>,<Rx delay>

Commands implemented:
    idn?        #identify tower
    rssi        #tower provides RSSI value in dBmW
    rec?        #request for next record
    rly         #open or close the relay
    rly?        #query for status of the relay
    dout        #program logic 1 or 0 to digital output
    dout?       #query for status of the dout
    adc?        #measure Voltage at ADC

An example of a sequence is below:
    rec?,1,250      #This would be the "rec?" command for tower 1 with a 250ms Rx delay
    1.0             #Then it would be a delay of 1.0 seconds
    rssi?,2,200     #Then it will request the RSSI from Tower2 with an RX delay of 200ms.
    adc?,3,100      #Find the ADC voltage measurement (for Tower battery).
    dout,1,0        #Program logic 0, to digital output of tower 1
    rly,1,0         #Open relay of Tower 1
    dout,4,1        #Program logic 1, to digital output of tower 4
    rly,3,1         #close relay of Tower 3

For executing the sequence just click the "Run Sequence" button in the GUI provided. You can change the text file, save the change with Ctrl-S, then click the "Run Sequence" button to execute the new sequence.


## Our Progress Updates

You can find our high level overview of the project here: https://www.youtube.com/watch?v=wtzndHTvqv8

1. Project Specification: 
    1a. https://docs.google.com/presentation/d/1rlrF-Zuk8p0degKV_BGiEk48ORhYCIDA/edit?slide=id.p1#slide=id.p1
    1b. https://docs.google.com/document/d/13GV29LR_JnSzSbaTRQxBC8bjlyIC4x5Hlyra8LaIjlw/edit?usp=sharing 
2. Class 3 Update: https://docs.google.com/presentation/d/1tn522-ccPfF0PuA8ECHO4EWBZsON5qdhE9HKgeI6YWs/edit?usp=sharing
3. Aloha Comms (OBSOLETE, we did NOT implement this): https://docs.google.com/presentation/d/1M_5ZPVamI-5GrK4w6aqMZWRMH9PsixXQQzIlKPegx9o/edit?usp=sharing
4. Class 4 Update: https://docs.google.com/presentation/d/1U22zahnXzea-_TtttLTYPjRHWydvcxEQ-rZrhlGyZck/edit?usp=sharing
5. Storyboard for Final Video (A bit out of date but has some good stuff in it): https://docs.google.com/presentation/d/1r4EZlPcA3uT00nvESWdwa3RRPi60Ocnsybh1oKXIWMg/edit?usp=sharing
6. Class 5 Update: https://docs.google.com/presentation/d/1zHdcEoeZQuuhZqUOibNKApxR4yRty7f_wuiGV6WtXbo/edit?usp=sharing


## Future Changes

The following changes are recommended and possible (in no particular order of importance):
1. Channel Hopping. Channel hopping would be extremely nice so you can send more data.

    **IMPORTANT DISCLAIMER**: We may not be 100% FCC compliant right now with single channel at 125kHz bandwidth. It is hard to find out a lot of information on what is required for LoRaWAN in terms of channel hopping and dwell times. We know 400ms is the maximum length of a message, but you may need to wait 20 seconds to send another message on the same channel, so adding a channel hopping scheme would be extremely helpful.
    See the Updates to see our LoRa research and sources. Class 5 Update has the most up to date research posted.
    Also see the section below for a discussion with Prof. Pannuto about channel hopping.

    Switching to a 500kHz bandwidth should allow you to stay FCC compliant (with 20dbm power) since it is no longer in the narrowband signal category. You could use any of the 8 500kHz uplink or 8 500kHz downlink channels for this. Note that range will be a bit worse for 500kHz bandwidth (compared to the 125kHz we tested with). These 500kHz Uplink channels are 903.0 to 914.0MHz (separated by 1.6MHz [1,600kHz]) and the 500kHz Downlink channels are 923.3MHz to 927.5MHz(separated by 0.6MHz [600kHz]).

2. LoRa Attributes. We added LoRaAttributes.py which has all possible LoRa attrubutes (except Power level). Implementing this (or a similar file) would be a great addition.

3. We kept the packet structure basic so as you can easily update it in the future and in case it does not work properly. This allows you to add more parameters to be sent from the Tower to GCS if you desire (e.g. temperature). To optimize, you can adjust the MAC layer to be only the number of bits required per data type sent and send data in bits. This would increase throughput since only meaningful data would be sent. For example, you likely only need 8 digits (5 or fewer digits after decimal) for lat/long since 1.1m precision probably beats the accuracy of the system as a whole. This would only require ~25/26 bits of info, which is less than the 32 bits in a float. This can be similarly optimized for altitude and other data types sent.
4. Logic so that a duplicate records cannot be entered into the csv on GCS (GCS_data.csv).
5. Currently an issue where lock is released when already released in pyTower.py, but this is not an issue that really impacts performance, just clogs the terminal output a bit.
6. Update the code so that it runs on system boot (Towers only).


## Updating to send other record structures

Currently, the database is set to store information in the following order:
    TowerID,    deviceID,   sample number,  timestamp,  latitude,   longitude,  altitude
The record sends a record the following order:
    sample_num, tower_id,   device_id,  time_stamp,   latitude, longitude,  altitude

The easiest way to send "different" data is to use the lat/lon/alt entries for different values. For example if you want to update this to a bird listening system where you send the bird that was sent, you could send a lat=1 for cardinal, lat = 2 for hawk, etc. and use "0" or null for the lon/alt values. 

If this is not sufficient (you need to add more values or want to make sure the labels are descriptive), you will need to update the following files to send a different MAC layer record:
1. database.py: You need to update the file such that a record has more/fewer items in the array.
2. pyTower.py expects 7 fields, you will need to update the file to accept the new number (and type).
3. tower.cpp: Expects 7 comma delineated fields in a record, you will need to update this.
4. gcs.cpp: Same as tower.cpp.
5. gcs.py: Expects a record to have 7 values, need to update this.

## Prof Pannuto's response about channel hopping

REQUEST FOR INPUT:

Hi Professor Pannuto,

Thank you for teaching us last quarter! We really enjoyed your course and decided to use LoRa for our capstone project. We were wondering if you would be willing to provide some feedback and critiques to our project. Right now we are mainly concerned with ensuring we follow FCC regulations, but any insight would be greatly appreciated.

Our project is in support of a UCSD E4E research project called Radio Telemetry Towers (RTT). We are tasked with sending location records from multiple stationary towers to a central computer. We have currently configured the system to use a single 125kHz bandwidth channel for all the communications, ensuring dwell time for any single message is under 400ms. I revisited FCC Part 15.247(a)(1)(i) and it looks like we need at least 50 channels to hop to with our 125kHz bandwidth configuration to comply with regulations since it is narrowband (less than 500kHz). I did not see anything stating that single channel narrowband signals would be compliant. Is my understanding correct? If so, are there any legal requirements for the “random” aspect of the hopping?

I’m not sure if we will necessarily have time to implement channel hopping on our project (though I’d like to try if it is required for compliance), however I would like to be fully transparent with the students we hand off to so they can plan accordingly.

For additional information about our project, you can see the following update we made for the class here: 
https://docs.google.com/presentation/d/1zHdcEoeZQuuhZqUOibNKApxR4yRty7f_wuiGV6WtXbo/edit?usp=sharing

Thank you for your time and consideration.


RESPONSE:
It sounds like you're implementing your own LoRa stack? (Most LoRa stacks will/should do TheRightThing already)

I'd recommend reading the LoRaWAN Alliance document on regional regulations, it's the easiest "quick answer" document here: https://lora-alliance.org/wp-content/uploads/2020/11/lorawan_regional_parameters_v1.0.3reva_0.pdf 

tl;dr—You can use fewer than 50 channels if you reduce your transmit power. [Relatedly, it's not a coincidence that many battery-powered, LoRa edge devices have a peak transmit power of +20dBm....]
