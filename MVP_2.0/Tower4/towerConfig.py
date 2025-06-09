# towerConfig.py
# Constants for data on the Towers which will be sent using a LoRa device to the GCS

# Tower Constants
TOWER_ID                =   4                   #Transmitting Tower ID
DB_Name                 =   "tower4_data.db"    #Name of database. Update to match TOWER_ID

#Table printing format
COLUMN_NAMES = ["Sample Num", "Tower ID", "Device ID", "Timestamp", "Latitude", "Longitude", "Altitude"]
TABLE_HEADER = "{:<12} {:<12} {:<12} {:<25} {:<12} {:<12} {:<10}"
ROW_FORMAT = "{:<12} {:<12} {:<12} {:<25} {:<12.7f} {:<12.7f} {:<10.2f}"
DIVIDER_LINE = "-" * 100  # Length of the divider line

