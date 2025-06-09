# config.py for data from UP7000 to sending LoRa device

# Constants
TOWER_ID                =   1           #Transmitting Tower ID
SF                      =   10          #LoRa Spreading Factor
CHANNEL                 =   1           #LoRa Channel
COLLECTION_INTERVAL     =   1           #how often data is collected
TRANSMISSION_INTERVAL   =   15          #how often data is transmitted


#database information using SQLite
DB_Name = "tower_data.db"

#Data we will send from Tower to the GCS  
class DataRecord:
    #attributes
    unreceived_data = [] #Know how many records we have right now

    def __init__(self, tower_id, device_id, sample_num, time_stamp, latitude, longitude, altitude, ack=False):
        self.tower_id   = tower_id                  #ID of Tower sending data
        self.device_id  = device_id                 #ID of device being tracked
        self.sample_num = sample_num                #Sample number in database
        self.time_stamp = time_stamp                #Time the record was recorded
        self.latitude   = latitude                  #lat of device
        self.longitude  = longitude                 #long of device
        self.altitude   = altitude                  #alt of device
        self.ack        = ack                       #has the server received this yet?
        DataRecord.unreceived_data.append(self)     #add self to list of unreceived_data

    # Functions/methods that might be shared
    @classmethod    #not sure if this is needed
    def _mark_as_acknowledged(cls, sample_nums):
        cls.unreceived_data = [record for record in cls.unreceived_data 
                              if record.sample_num not in sample_nums]
