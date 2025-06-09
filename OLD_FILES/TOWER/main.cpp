#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>

/*~~~~~ Instance Configuration ~~~~*/
// Device profile
#define DEVICE_ID       0x01 //    CiC=0x00, 0x00 -> 0xFF
                             // Tower= 0x01 -> 0x40 {64d}
                             // EndDevice = 0x41 -> FF {256d}
#define FW_VER          0.04  
#define DEVICE_TYPE     "Tower" //"Tower", "End device"  
#define DEBUG_MODE      false       
#define DEBUG_MODE_SRX  true    
#define DEBUG_MODE_STX  false  
#define DEBUG_MODE_RX   false 
#define DEBUG_MODE_FIELDS   false  //false 
                     
// prefix JAMNET
#define IS_GATEWAY       0      // 0 means is end device
#define CHANNEL_UPLINK   10      // 0-63?
#define CHANNEL_DOWNLINK 11
#define JN_ADDRESS       0xCAFE // 16bit?

#define JN_LORA_SPREAD   7     // low spreading factor, fast TX
#define JN_LORA_BW       125.0 // bw?
#define JN_INIT_FREQ     902.5 // initial frequency for Radio.begin?
                               // not the right thing, we'll use tune_to_rx() to init properly

/*~~~~~Hardware Definitions~~~~~*/

// These are hardware specific to the Heltec WiFi LoRa 32 V3
// Cite: https://resource.heltec.cn/download/WiFi_LoRa32_V3/HTIT-WB32LA(F)_V3_Schematic_Diagram.pdf
#define PRG_BUTTON 0
#define LORA_NSS_PIN 8
#define LORA_SCK_PIN 9
#define LORA_MOSI_PIN 10
#define LORA_MISO_PIN 11
#define LORA_RST_PIN 12
#define LORA_BUSY_PIN 13
#define LORA_DIO1_PIN 14

/*~~~~~Radio Configuration~~~~~*/

// Initialize SX1262 radio
// Make a custom SPI device because *of course* Heltec didn't use the default SPI pins
SPIClass spi(FSPI);
SPISettings spiSettings(2000000, MSBFIRST, SPI_MODE0); // Defaults, works fine
SX1262 radio = new Module(LORA_NSS_PIN, LORA_DIO1_PIN, LORA_RST_PIN, LORA_BUSY_PIN, spi, spiSettings);

/*~~~~~Function Prototypes~~~~~*/
void error_message(const char* message, int16_t state);

/*~~~~~Interrupt Handlers~~~~~*/
volatile bool receivedFlag = false;
volatile bool buttonFlag = false;

// This function should be called when a complete packet is received.
//  It is placed in RAM to avoid Flash usage errors
#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void receiveISR(void) {
  // WARNING:  No Flash memory may be accessed from the IRQ handler: https://stackoverflow.com/a/58131720
  //  So don't call any functions or really do anything except change the flag
  receivedFlag = true;
}

// This function should be called when a complete packet is received.
//  It is placed in RAM to avoid Flash usage errors
#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void buttonISR(void) {
  // WARNING:  No Flash memory may be accessed from the IRQ handler: https://stackoverflow.com/a/58131720
  //  So don't call any functions or really do anything except change the flag
  buttonFlag = true;
}

/*~~~~~Helper Functions~~~~~*/
void error_message(const char* message, int16_t state) {
  Serial.printf("ERROR!!! %s with error code %d\n", message, state);
  while(true); // loop forever
}

/*====== My globals =====*/
String last_packet;
char extractedFields_ota[4][128];
char extractedFields_s[7][128];
int numFields;
int tower_id = 1; 
String tank = "";
String tank_s, tank_rf;
int rx_delay = 0;
int num_of_mess_to_Tx = 0;
String SessionRx_Data_USBc  = "";
#define NO_ERROR      0
#define SYNTAX_ERROR  1

// Will
unsigned long previousMillis = 0;
const long interval = 3000; 
unsigned long lastAdaptTime = 0;
unsigned int count = 0; 
volatile bool recievedSerialDataFlag = false;

void fillCharArrayWithNullMemset(char arr[][128], int rows, int cols) {
  for (int i = 0; i < rows; ++i)
    memset(arr[i], '\0', cols * sizeof(char));
}

enum LinkQuality {
  LINK_EXCELLENT,
  LINK_GOOD,
  LINK_FAIR,
  LINK_POOR
};

LinkQuality assessLinkQuality(float rssi, float snr) {
  if (snr > 7 && rssi > -90) return LINK_EXCELLENT;
  if (snr > 3 && rssi > -100) return LINK_GOOD;
  if (snr > 0 && rssi > -110) return LINK_FAIR;
  return LINK_POOR;
}

typedef enum {
  Q_IDN,
  Q_RSSI,
  CMD_OTA,
  Q_OTA,
  Q_DL,
  Q_UL,
  CMD_DL,
  CMD_UL,
  Q_REC,
  CMD_ACK,
  RECIEVED_ACK,
  CMD_UNKNOWN
} CommandType;

CommandType getCommandType(const char *command) {
  if (strcmp(command, "idn?"   ) == 0) return Q_IDN;
  if (strcmp(command, "rssi?" ) == 0) return Q_RSSI;
  if (strcmp(command, "ota"  ) == 0) return CMD_OTA;
  if (strcmp(command, "ota?"  ) == 0) return Q_OTA;
  if (strcmp(command, "dl?" ) == 0) return Q_DL;
  if (strcmp(command, "ul?") == 0) return Q_UL;
  if (strcmp(command, "dl" ) == 0) return CMD_DL;
  if (strcmp(command, "ul") == 0) return CMD_UL;
  if (strcmp(command, "rec?"   ) == 0) return Q_REC;
  if (strcmp(command, "acked"   ) == 0) return RECIEVED_ACK;
  if (strcmp(command, "ack"   ) == 0) return CMD_ACK;
  return CMD_UNKNOWN;
}

// Lora config
void configureLoRaAdaptive(LinkQuality quality) {

  // Always standby before reconfig
  radio.standby();  

  switch (quality) {
    case LINK_EXCELLENT:
      //radio.setSpreadingFactor(7);    
      radio.setCodingRate(5);        
      radio.setOutputPower(14);   
      break;

    case LINK_GOOD:
      //adio.setSpreadingFactor(8);
      radio.setCodingRate(6);        
      radio.setOutputPower(18);
      break;

    case LINK_FAIR:
      //radio.setSpreadingFactor(9);
      radio.setCodingRate(7);        
      radio.setOutputPower(20);
      break;

    case LINK_POOR:
      //radio.setSpreadingFactor(10);  
      radio.setCodingRate(8);         
      radio.setOutputPower(22);      
      break;
  }

  radio.setCRC(true);  
}


/*====== CHANNEL SCANNING =====*/
int curr_channel = -1;
// max channel = 40
float chan_i_to_freq(int chan) {
  return 902.3 + 0.2*chan;
}

// Function to extract fields from a comma-delimited string
int extractFields_ota(const char *inputString, char fields[][128], int maxFields) {
  fillCharArrayWithNullMemset(extractedFields_ota,4,128);
  char *token;
  char *rest = strdup(inputString); // Duplicate the string as strtok modifies it
  int fieldCount = 0;
  if (rest == NULL) {
      fprintf(stderr, "Error: Memory allocation failed\n");
      return -1; // Indicate an error
  }
  while ((token = strtok_r(rest, ",", &rest)) != NULL && fieldCount < maxFields) {
      strncpy(fields[fieldCount], token, 63); // Copy the token, prevent buffer overflow
      fields[fieldCount][63] = '\0';        // Null-terminate the string
      fieldCount++;
  }
  free(rest); // Free the duplicated string
  return fieldCount;
}

int extractFields_s(const char *inputString, char fields[][128], int maxFields) {
  fillCharArrayWithNullMemset(extractedFields_s,7,128);
  char *token;
  char *rest = strdup(inputString); // Duplicate the string as strtok modifies it
  int fieldCount = 0;
  if (rest == NULL) {
      fprintf(stderr, "Error: Memory allocation failed\n");
      return -1; // Indicate an error
  }
  while ((token = strtok_r(rest, ",", &rest)) != NULL && fieldCount < maxFields) {
      strncpy(fields[fieldCount], token, 63); // Copy the token, prevent buffer overflow
      fields[fieldCount][63] = '\0';        // Null-terminate the string
      fieldCount++;
  }
  free(rest); // Free the duplicated string
  return fieldCount;
}

void advance_channel() {
  curr_channel += 1;
  if (curr_channel > 40) { curr_channel = 0; }
  float freq = chan_i_to_freq(curr_channel);
  if (DEBUG_MODE) Serial.printf("Switching to channel %d, freq %f\n", curr_channel, freq);

  if (radio.setFrequency(freq) == RADIOLIB_ERR_INVALID_FREQUENCY) {
    Serial.println(F("Selected frequency is invalid for this module!"));
    while (true);
  }

  int state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Starting reception failed", state);
  }
}

void tune_to_channel(int ch) {
  float freq = chan_i_to_freq(ch);
  if (DEBUG_MODE) Serial.printf("Switching to channel %d, freq %f\n", ch, freq);

  if (radio.setFrequency(freq) == RADIOLIB_ERR_INVALID_FREQUENCY) {
    Serial.println(F("Selected frequency is invalid for this module!"));
    while (true);
  }

  int state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Starting reception failed", state);
  }
}

// Note: TX and RX are swapped for gateways and end devices, handle this
void tune_to_tx() { // Gateways transmits on downlink
  if (IS_GATEWAY) { tune_to_channel(CHANNEL_DOWNLINK); }
  else            { tune_to_channel(CHANNEL_UPLINK); }
}

void tune_to_rx() { // Gateway listens to uplink
  if (IS_GATEWAY) { tune_to_channel(CHANNEL_UPLINK); }
  else            { tune_to_channel(CHANNEL_DOWNLINK); }
}

int16_t Tx(String msg){
  tune_to_tx();
  int16_t state = radio.transmit(msg+"\r");
  if (state == RADIOLIB_ERR_NONE) {
    if (DEBUG_MODE) Serial.println("TX Complete!");
  } else if (state == RADIOLIB_ERR_PACKET_TOO_LONG) {
    // packet was longer than max size
    if (DEBUG_MODE) Serial.println("Packet too long to transmit");
  } else if (state == RADIOLIB_ERR_TX_TIMEOUT) {
    // timeout occurred while transmitting packet
    if (DEBUG_MODE) Serial.println("TX timeout occurred?");
  } else {
    // Some other error occurred
    if (DEBUG_MODE) Serial.printf("Error while transmitting! Error code: %d\n", state);
  }
  // transmitting drops us out of receiving mode as if we received a packet
  // reset the receivedFlag status and resume receiving
  tune_to_rx();
  return state;
}

void Tx_(String msg){
  int16_t res =  Tx(msg);
}

/*~~~~~Application~~~~~*/
void setup() {
  Serial.begin(115200);

  // Set up GPIO pin for "PRG" button and enable interrupts for it
  pinMode(PRG_BUTTON, INPUT);
  attachInterrupt(PRG_BUTTON, buttonISR, FALLING);

  // Set up SPI with our specific pins
  spi.begin(LORA_SCK_PIN, LORA_MISO_PIN, LORA_MOSI_PIN, LORA_NSS_PIN);

  Serial.print("Initializing radio...");
  int16_t state = radio.begin(JN_INIT_FREQ, JN_LORA_BW, JN_LORA_SPREAD, 5, 0x34, 0, 8);
  if (state != RADIOLIB_ERR_NONE) {
      error_message("Radio initializion failed", state);
  }

  // Current limit of 140 mA (max)
  state = radio.setCurrentLimit(140.0);
  if (state != RADIOLIB_ERR_NONE) {
      error_message("Current limit intialization failed", state);
  }

  // Hardware uses DIO2 on the SX1262 as an RF switch
  state = radio.setDio2AsRfSwitch(true);
  if (state != RADIOLIB_ERR_NONE) {
      error_message("DIO2 as RF switch intialization failed", state);
  }

  // LoRa explicit header mode is used for LoRaWAN
  state = radio.explicitHeader();
  if (state != RADIOLIB_ERR_NONE) {
      error_message("Explicit header intialization failed", state);
  }

  // LoRaWAN uses a two-byte CRC
  state = radio.setCRC(2);
  if (state != RADIOLIB_ERR_NONE) {
      error_message("CRC intialization failed", state);
  }
  Serial.println("Complete!");

  // ========== List boot info
  if(IS_GATEWAY) {
    String msg = "### Starting Ground Control Station (GCS) #"+String(DEVICE_ID)+", listening on uplink channel: "+String(CHANNEL_UPLINK);
    Serial.println(msg);Tx_(msg);
    tune_to_rx();
  } else {
    String msg = "### Starting TOWER #"+String(DEVICE_ID)+", listening on downlink channel: "+String(CHANNEL_DOWNLINK);
    Serial.println(msg);
    int16_t res =  Tx(msg);
    delay(200);
    tune_to_rx();
  }

  // set the function that will be called when a new packet is received
  radio.setDio1Action(receiveISR);

  // start continuous reception
  Serial.print("Beginning continuous reception...");
  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Starting reception failed", state);
  }
  Serial.println("Complete!");
}

void ack_incoming_serial_data(){
  if (millis() - lastAdaptTime > 5000) {  // Every 5 seconds

    Serial.write("ackS");

    lastAdaptTime = millis();
  }
}

void adjustLinkQuality() {
  if (millis() - lastAdaptTime > 5000) {  // Every 5 seconds
    float rssi = radio.getRSSI();
    float snr  = radio.getSNR();

    //Serial.println("rssi=" + String(rssi));
    //Serial.println("snr=" + String(snr));

    LinkQuality quality = assessLinkQuality(rssi, snr);
    configureLoRaAdaptive(quality);
    lastAdaptTime = millis();
  }
}


void parse_s_command(const char *command){
  switch (getCommandType(command)) {
    case Q_IDN:
      if (numFields>=1){
        Serial.println("Device type: "+String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER));
        delay(100);
      }
      break;     
    default:
        //String msg = "Invalid Command or syntax error";
        //Serial.println(msg);
        break;
}
//
delay(10);
}

void handle_button_press(){
  //send a sample record for now
  String s = "1,2,34,2025-04-20 16:55:12,12.1234567,123.123456,12.12";
  int16_t state = Tx(s);
  String msg = "Device type: "+String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER)+", Channels: Uplink: "+String(CHANNEL_UPLINK)+ "/ Downlink: "+String(CHANNEL_DOWNLINK);   

  if (state == RADIOLIB_ERR_NONE) {
      Serial.println(msg);
    } else if (state == RADIOLIB_ERR_PACKET_TOO_LONG) {
      // packet was longer than max size
      Serial.println("Packet too long to transmit");
    } else if (state == RADIOLIB_ERR_TX_TIMEOUT) {
      // timeout occurred while transmitting packet
      Serial.println("TX timeout occurred?");
    } else {
      // Some other error occurred
      Serial.printf("Error while transmitting! Error code: %d\n", state);
    }

  receivedFlag = false;
  tune_to_rx();
  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Resuming reception failed", state);
  }
}



void handle_serial(){
  String receivedData = "";
  char c;
  while (Serial.available() > 0) {
      c = Serial.read(); // Read a single character        
      if( c == '\n' ||  c == '\r' )
        break;
      receivedData += c;        
      delay(2); // Small delay to allow buffer to fill properly
  } 
  tank_s += receivedData;
  if (receivedData.startsWith("data") && (num_of_mess_to_Tx > 0)){
    Tx(receivedData);
    num_of_mess_to_Tx = num_of_mess_to_Tx - 1;
  }  

  if (c == '\n') { //~
    SessionRx_Data_USBc += tank_s + "\n";
    if (DEBUG_MODE_FIELDS) 
        Serial.println("found new line, tank_s ["+tank_s+"]");

    const char *dataString = tank_s.c_str();   
    numFields = extractFields_s(dataString, extractedFields_s, 7);//char extractedFields_s[4][128]; // Assuming a maximum of 4 fields, each max 63 chars + null
    if (DEBUG_MODE_FIELDS) 
        Serial.println("numFields = ["+String(numFields)+"]");
      if (numFields == 7) {
          if (DEBUG_MODE_FIELDS) Serial.printf("Found %d fields:\n", numFields);
          for (int i = 0; i < numFields; i++) {
              if (DEBUG_MODE_FIELDS) Serial.printf("Field %d: %s\n", i + 1, extractedFields_s[i]);
                // Example of converting to other data types if needed
                if (i == 1) {
                    int numericValue = atoi(extractedFields_s[i]);
                    if (DEBUG_MODE_FIELDS) Serial.printf("  As Integer: %d\n", numericValue);
                } else if (i == 2) {
                    float floatValue = atof(extractedFields_s[i]);
                    if (DEBUG_MODE_FIELDS) Serial.printf("  As Float: %.2f\n", floatValue);
                }
          }
        //Transmit to GCS
        String D = ",";
        int16_t res = Tx(String(extractedFields_s[0])+D+String(extractedFields_s[1])+D+String(extractedFields_s[2])+D+String(extractedFields_s[3])+D+String(extractedFields_s[4])+D+String(extractedFields_s[5])+D+String(extractedFields_s[6]));
        Serial.println("ok");
        delay(50);
      } 
      else if (numFields >= 1) {
        if (DEBUG_MODE_FIELDS) Serial.printf("Found %d fields:\n", numFields);
        for (int i = 0; i < numFields; i++) {
            if (DEBUG_MODE_FIELDS) Serial.printf("Field %d: %s\n", i + 1, extractedFields_s[i]);
        }
        parse_s_command(extractedFields_s[0]);       
      } 

      tank_s = "";
  } //~     

}

void parse_ota_command(const char *command){
  switch (getCommandType(command)) {
    case Q_REC:
        if (numFields==3){
        int device_id = atoi(extractedFields_ota[1]);
        //Serial.println(device_id + "zzzz");
        //Serial.println(tower_id + "ppppp");
        if (device_id == tower_id)
          num_of_mess_to_Tx = atoi(extractedFields_ota[2]);
          Serial.print("GCSrec," );  
          Serial.print(num_of_mess_to_Tx);
          Serial.println();
        }
      break;
    case RECIEVED_ACK:

      if (numFields==3){
        rx_delay = atoi(extractedFields_ota[2]);
        int device_id = atoi(extractedFields_ota[1]);
        if (device_id == tower_id)
        //if (device_id == int(DEVICE_ID))
          Serial.println("GCSackS");
      }
      break;
    case Q_IDN:
      //Serial.println("Device type: "+String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER)+" , Channels: Uplink: "+String(CHANNEL_UPLINK)+ "/ Downlink: "+String(CHANNEL_DOWNLINK));
      if (numFields>=3){
        rx_delay = atoi(extractedFields_ota[2]);
        int device_id = atoi(extractedFields_ota[1]);
        //Serial.println("Executing CMD_IDN -> "+String(extractedFields_ota[0])+","+String(extractedFields_ota[1])+","+String(extractedFields_ota[2]));
        if (device_id == DEVICE_ID)
          int16_t res = Tx("Device type: "+String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER)+", Channels: Uplink: "+String(CHANNEL_UPLINK)+ "/ Downlink: "+String(CHANNEL_DOWNLINK));
        
        delay(rx_delay);
      }
      break;
    case Q_RSSI:
      if (numFields>=3){
        rx_delay = atoi(extractedFields_ota[2]);
        int device_id = atoi(extractedFields_ota[1]);
        if (device_id == DEVICE_ID)
          int16_t res = Tx(String(radio.getRSSI()));

        delay(rx_delay);  
      }
      break;
    case CMD_OTA:
      if (numFields>=2){
        int device_id = atoi(extractedFields_ota[1]);
        if (device_id == DEVICE_ID)
          int16_t res = Tx("Executing OTA configuration command not implemented yet.");

        delay(rx_delay);  
      }
      break;
    case Q_OTA:
      if (numFields>=2){
        int device_id = atoi(extractedFields_ota[1]);
        if (device_id == DEVICE_ID)
          int16_t res = Tx("OTA query: OTA configuration command not implemented yet.");

        delay(rx_delay);  
      }
      break;
    case Q_DL:///
      if (numFields>=2){
        int device_id = atoi(extractedFields_ota[1]);
        if (device_id == DEVICE_ID)
          int16_t res = Tx("Downlink: "+String(CHANNEL_DOWNLINK));     
      }
      break;
    case Q_UL:
        if (numFields>=2){
          int device_id = atoi(extractedFields_ota[1]);
          if (device_id == DEVICE_ID)
            int16_t res = Tx("Uplink: "+String(CHANNEL_UPLINK));     
        }
        break;
    case CMD_DL:
        if (numFields>=3){
          int device_id = atoi(extractedFields_ota[1]);
          if (device_id == DEVICE_ID)
            int16_t res = Tx("Change channel Downlink to: "+String(extractedFields_ota[2]));  
        }
        break;
    case CMD_UL:
        if (numFields>=3){
          int device_id = atoi(extractedFields_ota[1]);
          if (device_id == DEVICE_ID)
            int16_t res = Tx("Change channel Uplink to: "+String(extractedFields_ota[2]));  
        }
        break;
    default:
        //String msg = "Invalid Command or syntax error";
        //Serial.println(msg);
        break;
}
//
delay(10);
}

void handle_ota_packet(){
  String packet_data = "";    
  fillCharArrayWithNullMemset(extractedFields_ota,4,128 );
  int state = radio.readData(packet_data);
  if (state == RADIOLIB_ERR_NONE) {
    // packet was successfully received
    const char *dataString = packet_data.c_str();
    //char extractedFields_ota[4][64]; // Assuming a maximum of 4 fields, each max 63 chars + null
    if (packet_data != ""){ 
      adjustLinkQuality();
    }
    numFields = extractFields_ota(dataString, extractedFields_ota, 4);

    if (numFields >= 3) {
        if (DEBUG_MODE_FIELDS) Serial.printf("Found %d fields:\n", numFields);
        for (int i = 0; i < numFields; i++) {
          if (DEBUG_MODE_FIELDS) Serial.printf("Field %d: %s\n", i + 1, extractedFields_ota[i]);
            // Example of converting to other data types if needed
            if (i == 1) {
                int numericValue = atoi(extractedFields_ota[i]);
                if (DEBUG_MODE_FIELDS) Serial.printf("  As Integer: %d\n", numericValue);
            } else if (i == 2) {
                float floatValue = atof(extractedFields_ota[i]);
                if (DEBUG_MODE_FIELDS) Serial.printf("  As Float: %.2f\n", floatValue);
            }
        }
        parse_ota_command(extractedFields_ota[0]);
        fillCharArrayWithNullMemset(extractedFields_ota,4,128 );          
    } else if (numFields == 0) {
      if (DEBUG_MODE_FIELDS) Serial.println("No fields found in the string.");
    } else {
      if (DEBUG_MODE_FIELDS)
        Serial.println("Error extracting fields: "+String(extractedFields_ota[0])+","+String(extractedFields_ota[1])+","+String(extractedFields_ota[2]));
    }
    if (DEBUG_MODE_RX){
      Serial.println("Received packet!");
      // print the data of the packet
      Serial.println("{"+packet_data+"}");//Serial.print("{");Serial.print(packet_data);Serial.println("}");

      packet_data = "";
    } 
    } else if (state == RADIOLIB_ERR_RX_TIMEOUT) {
    // timeout occurred while waiting for a packet
    Serial.println("timeout!");
  } else if (state == RADIOLIB_ERR_CRC_MISMATCH) {
    // packet was received, but is malformed
    Serial.println("CRC error!");
  } else {
    // some other error occurred
    Serial.print("failed, code ");
    Serial.println(state);
  }

  // resume listening
  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Resuming reception failed", state);
  }

}


void loop() {
  // Handle OTA packet receptions
  if (receivedFlag) {
    receivedFlag = false;
    handle_ota_packet(); 
  }


  // Handle USBs
  if (Serial.available() > 0) { // Check if data is available to read
    handle_serial();
  }
  //--
}

