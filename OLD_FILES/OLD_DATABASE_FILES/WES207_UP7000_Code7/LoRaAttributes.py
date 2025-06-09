#LoRaAttributes.py

import json
import os
import math

#Initialize data. These will be the default values on bootup if no previous values are saved.
SF_DEFAULT                      =   10                  #LoRa Spreading Factor
CHANNEL_DEFAULT                 =   0                   #LoRa Channel
FREQ_DEFAULT                    =   902.3               #Freq of channel 0 in MHz
RECORDS_PER_PKT_DEFAULT         =   1                   #Number of records sent each LoRa Tx
CODING_RATE_DEFAULT             =   (4,5)               #default coding rate is 4/5
BANDWIDTH_DEFAULT               =   125                 #[kHz] BW of LoRa channel
PREAMBLE_LEN_DEFAULT            =   8                   #default preamble length
EXPLICIT_HEADER_DEFAULT         =   False               #default explicit header
CRC_DEFAULT                     =   True                #Use CRC as default
LOW_DATA_RATE_DEFAULT           =   False               #LDR_optimization assumed false. Will not be used in this doc.
PAYLOAD_LENGTH_PER_PKT          =   10                  #[bytes] if 1 record sent. TO DO: FIX THIS based on what we actually send. This is a PLACEHOLDER!
MAXIMUM_DWELL_TIME              =   400.000             #[ms] legal maximum dwell time on channel
LORA_CONFIG_FILE                =   "lora_config.json"  #config file to store lora values


#this class is how we load previous LoRa attributes on bootup, save current LoRa attributes, update LoRa attributes, and check if
#requested LoRa attributes will be FCC compliant
class LoRaAttributes:
    def __init__(self):
        #Load data from json file (if exists). This is to remember LoRa attributes after power cycling.
        if os.path.exists(LORA_CONFIG_FILE):
            self._load_config()
        else:
            self.sf = SF_DEFAULT
            self.channel = CHANNEL_DEFAULT
            self.carrier_frequency = FREQ_DEFAULT
            self.records_per_pkt = RECORDS_PER_PKT_DEFAULT
            self.coding_rate = CODING_RATE_DEFAULT
            self.bandwidth = BANDWIDTH_DEFAULT
            self.preamble_len = PREAMBLE_LEN_DEFAULT
            self.explicit_header = EXPLICIT_HEADER_DEFAULT
            self.crc = CRC_DEFAULT
            self.ldr_opt = LOW_DATA_RATE_DEFAULT
            self.payload_len = PAYLOAD_LENGTH_PER_PKT     
            self.dwell_time = self._calculate_dwell_time() 
            self._save_config()
    
    def __str__(self):
        return (f"LoRa Configuration:\n"
                f"Spreading Factor: {self.sf}\n"
                f"Channel: {self.channel}\n"
                f"Carrier Frequency: {self.carrier_frequency}MHz\n"
                f"Records per Packet: {self.records_per_pkt}\n"
                f"Coding Rate: {self.coding_rate}\n"
                f"Bandwidth: {self.bandwidth}kHz\n"
                f"Preamble Length: {self.preamble_len} Symbols\n"
                f"Explicit Header: {self.explicit_header}\n"
                f"CRC: {self.crc}\n"
                f"Low Data Rate Optimization: {self.ldr_opt}\n"
                f"Payload Length: {self.payload_len} Bytes\n"
                f"Dwell Time: {self.dwell_time}ms\n"
        )

    # Save and Load LoRa configuration
    def _save_config(self):
        '''save current LoRa configuration as a dictionary to LORA_CONFIG_FILE.json'''
        config = {
            "SF": self.sf,
            "channel": self.channel,
            "carrier_frequency": self.carrier_frequency,
            "records_per_pkt": self.records_per_pkt,
            "coding_rate": self.coding_rate,
            "bandwidth": self.bandwidth,
            "preamble_len": self.preamble_len,
            "explicit_header": self.explicit_header,
            "crc": self.crc,
            "ldr_opt": self.ldr_opt,
            "payload_len": self.payload_len,
            "dwell_time": self.dwell_time
        }
        with open(LORA_CONFIG_FILE, "w") as file:
            json.dump(config, file)
    def _load_config(self):
        '''Load previous LoRa config if exists. If not exist, load initial values.'''
        #Note: Values should always exist, but get() allows to default back to original if file is corrupted upon power cycling.
        with open(LORA_CONFIG_FILE, "r") as file:
            config = json.load(file)
            self.sf = config.get("SF", SF_DEFAULT)
            self.channel = config.get("channel", CHANNEL_DEFAULT)
            self.carrier_frequency = config.get("carrier_frequency", FREQ_DEFAULT)
            self.records_per_pkt = config.get("records_per_pkt", RECORDS_PER_PKT_DEFAULT)
            self.coding_rate = config.get("coding_rate", CODING_RATE_DEFAULT)
            self.bandwidth = config.get("bandwidth", BANDWIDTH_DEFAULT)
            self.preamble_len = config.get("preamble_len", PREAMBLE_LEN_DEFAULT)
            self.explicit_header = config.get("explicit_header", EXPLICIT_HEADER_DEFAULT)
            self.crc = config.get("crc", CRC_DEFAULT)
            self.ldr_opt = config.get("ldr_opt", LOW_DATA_RATE_DEFAULT)
            self.payload_len = config.get("payload_len", PAYLOAD_LENGTH_PER_PKT)
            self.dwell_time = config.get("dwell_time", self._calculate_dwell_time())
    
    #Dwell Time Methods
    def _calculate_dwell_time(self):
        # example: https://github.com/ifTNT/lora-air-time
        bw_hz = self.bandwidth * 1000
        T_sym = (2**self.sf / bw_hz) * 1000 #symbol duration in [ms]
        preamble_symbols = self.preamble_len + 4.25 #sync word is 4.25 symbols

        payload_bits = 8 * self.payload_len
        if self.crc:
            payload_bits += 16
        if self.explicit_header:
            payload_bits += 20

        num, denom = self.coding_rate
        payload_bits_with_coding = payload_bits * denom / num

        bits_per_symbol = self.sf   #bits per symbol. IGNORE LDR_OPT FOR NOW, just assume always off.

        #number of symbols to tx payload
        payload_symbols = 8  # Constant for sync word
        payload_symbols += math.ceil(payload_bits_with_coding / bits_per_symbol)
        time = (preamble_symbols + payload_symbols) * T_sym
        self.dwell_time = round(time, 3) #round to 3 decimal places.
        print(f"Dwell time estimated to be {self.dwell_time}ms.\n")
        return self.dwell_time

    def _is_dwell_time_legal(self):
        '''Make sure we do not pass 400ms dwell time based on SF, packet structure, etc.'''
        #Determine if new requested setup is legal
        new_dwell_time = self._calculate_dwell_time()
        if (new_dwell_time > MAXIMUM_DWELL_TIME):
            print(f"Dwell time is longer than {MAXIMUM_DWELL_TIME}ms. Will not change value.\n")
            return False
        else:
            print(f"Dwell time is less than {MAXIMUM_DWELL_TIME}ms. Will update paramater value shortly.\n")
            return True


    #SET VALUES. Return 1 if set successfully, return 0 if not FCC compliant and retaining previous values.
    def set_sf(self,new_SF):
        #Check if 7 <= SF <= 10
        if new_SF > 10:
            print(f"Did not update SF to {new_SF} because SF cannot be above 10 and be FCC compliant.")
            return 0
        if new_SF < 7:
            print(f"Did not update SF to {new_SF} because 7 is the minimum SF.")
            return 0
        #Check if legal
        self.sf = new_SF
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"SF is now set to {self.sf}.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update SF to {new_SF} because it would not be FCC compliant.")
            print(f"SF is set to {self.sf}.\n")
            return 0       
  
    def set_channel(self,new_channel):
        '''Update LoRa Channel AND corresponding Carrier Frequency'''
        self.channel = new_channel
        self.carrier_frequency = FREQ_DEFAULT + self.channel*0.2
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Channel now set to {self.channel} with Carrier Frequency {self.carrier_frequency}.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update channel to {new_channel} because it would not be FCC compliant.")
            print(f"Channel is set to {self.channel}.\n")
            return 0

    def set_records_per_pkt(self, new_rec_per_pkt):
        self.records_per_pkt = new_rec_per_pkt
        self._set_payload_len() #update length of payload
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Now sending {self.records_per_pkt} records with every LoRa packet.\n")
            print(f"New payload length is {self.payload_len} bytes.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update to {new_rec_per_pkt} records per packet because it would not be FCC compliant.")
            print(f"Records per packet is set to {self.records_per_pkt}.\n")
            return 0 

    def set_coding_rate(self,new_cr):
        self.coding_rate = new_cr
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Coding Rate now set to {self.coding_rate}.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update Coding Rate to {new_cr} because it would not be FCC compliant.")
            print(f"SF is set to {self.sf}.\n")
            return 0 
    
    def set_bandwidth(self, new_bw):
        self.bandwidth = new_bw
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Bandwidth now set to {self.bandwidth}kHz.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update bandwidth to {new_bw} because it would not be FCC compliant.")
            print(f"Bandwidth is set to {self.bandwidth}kHz.\n")
            return 0 
    
    def set_preamble_len(self, new_preamble_len):
        self.preamble_len = new_preamble_len
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Preamble length now set to {self.preamble_len} Symbols.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update preamble length to {new_preamble_len} because it would not be FCC compliant.")
            print(f"Preamble Length is set to {self.preamble_len}.\n")
            return 0
    
    def set_explicit_header(self, new_EH):
        self.explicit_header = new_EH
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Explicit Header is now set to {self.explicit_header}.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update explicit header to {new_EH} because it would not be FCC compliant.")
            print(f"SF is set to {self.explicit_header}.\n")
            return 0
    
    def set_crc(self, new_crc):
        self.crc = new_crc
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"CRC now set to {self.crc}.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update CRC to {new_crc} because it would not be FCC compliant.")
            print(f"CRC is set to {self.crc}.\n")
            return 0
    
    def set_ldr_opt(self, new_ldr_opt):
        self.ldr_opt = new_ldr_opt
        if self._is_dwell_time_legal():
            self._save_config() #save to config file if legal
            print(f"Low data rate optimization now set to {self.ldr_opt}.\n")
            return 1
        else:
            self._load_config() #reload previous config if illegal
            print(f"Did not update low data rate optimization to {new_ldr_opt} because it would not be FCC compliant.")
            print(f"LDR Optimization is set to {self.ldr_opt}.\n")
            return 0 
    
    def _set_payload_len(self):
        '''only call this function through self.set_records_per_pkt()'''
        self.payload_len = self.records_per_pkt * PAYLOAD_LENGTH_PER_PKT
    


    #Get current LoRa configuration
    def get_LoRa_attributes(self):
        '''Return the current LoRa configuration. Use __str__ for readable version.'''
        return (self.sf, self.channel, self.carrier_frequency, self.records_per_pkt, self.coding_rate, self.bandwidth,
            self.preamble_len, self.explicit_header, self.crc, self.ldr_opt, self.payload_len, self.dwell_time
        )
        

