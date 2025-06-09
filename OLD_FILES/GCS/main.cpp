
#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>

/*~~~~~ USB Serial ~~~~*/
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"

/*~~~~~ Instance Configuration ~~~~*/
// Device profile
#define DEVICE_ID       0x00 
#define FW_VER          0.03  
#define DEVICE_TYPE     "Ground Control Station"     
#define DEBUG_MODE      false   
#define DEBUG_MODE_SRX  false    
#define DEBUG_MODE_STX  false 
#define DEBUG_MODE_FIELDS      false                    
// prefix JAMNET
#define IS_GATEWAY        1      
#define CHANNEL_UPLINK   10      
#define CHANNEL_DOWNLINK 11
#define JN_ADDRESS       0xCAFE // 16bit?

#define JN_LORA_SPREAD   7     // low spreading factor, fast TX
#define JN_LORA_BW       125.0 // bw?
#define JN_INIT_FREQ     902.5 
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
  //~printf("ERROR!!! %s with error code %d\n", message, state);
  while(true); // loop forever
}

/*====== My globals =====*/
//String last_packet = "";
//#define BUFF_SZ 100  // Define the buffer size
//char tank[BUFF_SZ] = {0};  // Initialize all elements to '\0'
char extractedFields[4][128]; // Assuming a maximum of 4 fields, each max 63 chars + null
int numFields;
String tank_s, tank_rf;
int rx_delay = 0;
String SessionRx_Data_USBc  = "";
volatile bool startTowerCycle = false;
int num_of_mess = 4;
int mess_counter = 0;
#define NO_ERROR      0
#define SYNTAX_ERROR  1

//testing
unsigned long lastAdaptTime = 0;

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
  return LINK_POOR;
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
  CMD_UNKNOWN
} CommandType;

// Function to get command type from string
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
      //Serial.println("Link Excellent configuring for data rate" );
      break;

    case LINK_GOOD:
      //radio.setSpreadingFactor(8);
      radio.setCodingRate(6);        
      radio.setOutputPower(18);
      //Serial.println("Link Good configuring for speed and distance" );
      break;

    case LINK_FAIR:
      //radio.setSpreadingFactor(9);
      radio.setCodingRate(7);        
      radio.setOutputPower(20);
      //Serial.println("Link Good configuring for balance" );
      break;

    case LINK_POOR: 
      //radio.setSpreadingFactor(10); 
      radio.setCodingRate(8);          
      radio.setOutputPower(22); 
      //Serial.println("Link Poor configuring for robustness" );     
      break;
  }

  radio.setCRC(true);  
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

/*====== CHANNEL SCANNING =====*/
int curr_channel = -1;
// max channel = 40
float chan_i_to_freq(int chan) {
  return 902.3 + 0.2*chan;
}

// Function to extract fields
int extractFields(const char *inputString, char fields[][128], int maxFields) {
  fillCharArrayWithNullMemset(extractedFields, 4,128);
  char *token;
  char *rest = strdup(inputString);
  int fieldCount = 0;
  if (rest == NULL) {
      fprintf(stderr, "Error: Memory allocation failed\n");
      return -1; // Indicate an error
  }
  while ((token = strtok_r(rest, ",", &rest)) != NULL && fieldCount < maxFields) {
      strncpy(fields[fieldCount], token, 63);
      fields[fieldCount][63] = '\0';        
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
  delay(2);
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
  tune_to_rx();
  return state;
}

void Tx_(String msg){
  int16_t res =  Tx(msg);
}

void handle_ota_data(String packet_data){
  if (packet_data.startsWith("data")) {
    Serial.println(packet_data);
    mess_counter = mess_counter - 1;
  }
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
    String msg = "### Starting Ground Control Station (GCS) #"+String(DEVICE_ID)+", listening on uplink channel: "+String(CHANNEL_UPLINK)+"\n";
    Serial.print(msg);
    //Tx_(msg);
    tune_to_rx();
  } else {
    String msg = "### Starting TOWER #"+String(DEVICE_ID)+", listening on downlink channel: "+String(CHANNEL_DOWNLINK)+"\n";
    Serial.print(msg);
    //Tx_(msg);
    tune_to_rx();
  }

  // set the function that will be called when a new packet is received
  radio.setDio1Action(receiveISR);

  // time
  /*
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time");
    return;
  }
  Serial.println(&timeinfo, "%A, %B %d %Y %H:%M:%S");
  */

  // start continuous reception
  Serial.print("Beginning continuous reception...");
  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Starting reception failed", state);
  }
  Serial.println("Complete!");




}

void parse_command(const char *command){
    switch (getCommandType(command)) {
      case Q_IDN:
        if (numFields>=3){
          rx_delay = atoi(extractedFields[2]);
          int device_id = atoi(extractedFields[1]);
          if (device_id == DEVICE_ID)
            Serial.println("Device type: "+String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER)+", Channels: Uplink: "+String(CHANNEL_UPLINK)+ "/ Downlink: "+String(CHANNEL_DOWNLINK));
          else
            int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]) + "," + String(extractedFields[2]));

        }
        break;
      //Sends acks back to the towers for the data recieved
      case CMD_ACK:
          if (numFields==3){
            rx_delay = atoi(extractedFields[2]);
            int device_id = atoi(extractedFields[1]);
            //Serial.println("Executing CMD_ACK -> "+String(extractedFields[0])+","+String(extractedFields[1])+","+String(extractedFields[2]));
            //Serial.println(String(extractedFields[1]) + "zzzzzzzzzz");
            int16_t res = Tx("acked," + String(extractedFields[1])+ "," + String(extractedFields[2]));
            delay(rx_delay);
          }
          break;              
      case Q_RSSI:
        if (numFields>=3){
          rx_delay = atoi(extractedFields[2]);
          int device_id = atoi(extractedFields[1]);
          //~Serial.println("Executing CMD_RSSI -> "+String(extractedFields[0])+","+String(extractedFields[1])+","+String(extractedFields[2]));
          if (device_id == DEVICE_ID)
            Serial.println(String(radio.getRSSI()));
          else
            int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));

        }
        break;
      case CMD_OTA:
          Serial.println("Executing OTA configuration command not implemented yet.");
          break;
      case Q_OTA:
          Serial.println("OTA query: OTA configuration command not implemented yet.");
          break;
      case Q_DL:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println("Downlink: "+String(CHANNEL_DOWNLINK));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;
      case Q_UL:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println("Uplink: "+String(CHANNEL_UPLINK));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;
      case CMD_DL:
          if (numFields>=3){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println("Change channel Downlink to: "+String(extractedFields[2]));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;
      case CMD_UL:
          if (numFields>=3){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println("Change channel Uplink to: "+String(extractedFields[2]));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;  
      // sends the request data in for on example: "rec?,1,4" 1 is the tower number and 4 is the amount of records requested
      case Q_REC:
          if (numFields>=3){
            rx_delay = atoi(extractedFields[2]);
            int device_id = atoi(extractedFields[1]);
            //Serial.println("Executing Q_REC -> "+String(extractedFields[0])+","+String(extractedFields[1])+","+String(extractedFields[2]));
            int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]) + "," + String(extractedFields[2]));
          }
          break;
    
          
      default:
          Serial.print("Syntax error: ");//Serial.println("Unknown command");
          String myString = String(command);
          Serial.println(myString);
          break;
  }
}

void handle_ota_packet(){
  // you can receive data as an Arduino String
  //String packet_data = "\0";
  String packet_data = "";
  delay(rx_delay);//Serial.printf("\r<delay: %d>\n", rx_delay);
  int state = radio.readData(packet_data);
  //tank_rf += packet_data;
  if (state == RADIOLIB_ERR_NONE) {
    //Serial.println("packet info from inside gcs func:" + packet_data);
    receivedFlag = false; //worked great!!, seems like the flag gets set multiple times during same transmision string
   
    if (packet_data != ""){ 
      adjustLinkQuality();
      handle_ota_data(packet_data);
    }


  } 
  else if (state == RADIOLIB_ERR_RX_TIMEOUT) {
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


void handle_button_press(){
  int i = 1;
  String id = String(i);
  String mesg = "rec?," + id + "," +String(num_of_mess);
  Tx(mesg);
  Serial.println(mesg);
}

void handle_usb_recieve(){
  String receivedData = "";
  char c;
  while (Serial.available() > 0) {
      c = Serial.read(); // Read a single character        
      if( c == '\n' ||  c == '\r' )
        break;
      receivedData += c;        
      delay(2); // Small delay to allow buffer to fill properly
  } 
    Serial.println(receivedData);
    tank_s += receivedData;
    if (c == '\n') { //~
      SessionRx_Data_USBc += tank_s + "\n";
      if (DEBUG_MODE_FIELDS) 
          Serial.println("found new line, tank_s ["+tank_s+"]");

      const char *dataString = tank_s.c_str(); 
      numFields = extractFields(dataString, extractedFields, 4);//char extractedFields[4][128]; // Assuming a maximum of 4 fields, each max 63 chars + null
    
      if (DEBUG_MODE_FIELDS) 
          Serial.println("numFields = ["+String(numFields)+"]");
      if (numFields >= 3) {
          if (DEBUG_MODE_FIELDS) Serial.printf("Found %d fields:\n", numFields);
          for (int i = 0; i < numFields; i++) {
              if (DEBUG_MODE_FIELDS) Serial.printf("Field %d: %s\n", i + 1, extractedFields[i]);
                // Example of converting to other data types if needed
                if (i == 1) {
                    int numericValue = atoi(extractedFields[i]);
                    if (DEBUG_MODE_FIELDS) Serial.printf("  As Integer: %d\n", numericValue);
                } else if (i == 2) {
                    float floatValue = atof(extractedFields[i]);
                    if (DEBUG_MODE_FIELDS) Serial.printf("  As Float: %.2f\n", floatValue);
                }
          }
          parse_command(extractedFields[0]);       
        } 
      else if (numFields >= 2) {
          
          if (DEBUG_MODE_FIELDS) Serial.printf("Found %d fields:\n", numFields);
          for (int i = 0; i < numFields; i++) {
              if (DEBUG_MODE_FIELDS) Serial.printf("Field %d: %s\n", i + 1, extractedFields[i]);
                // Example of converting to other data types if needed
                if (i == 1) {
                    int numericValue = atoi(extractedFields[i]);
                    if (DEBUG_MODE_FIELDS) Serial.printf("  As Integer: %d\n", numericValue);
                }
          }
          parse_command(extractedFields[0]);       
        } 
      else if (numFields >= 1) {
          if (DEBUG_MODE_FIELDS) Serial.printf("Found %d fields:\n", numFields);
          for (int i = 0; i < numFields; i++) {
              if (DEBUG_MODE_FIELDS) Serial.printf("Field %d: %s\n", i + 1, extractedFields[i]);
          }
          parse_command(extractedFields[0]);       
        }
       

      tank_s = "";
    }
}


void loop() {

  // Handle ota receptions
  if (receivedFlag) {
    receivedFlag = false;
    handle_ota_packet();
  }


  // Handle button presses
  if (buttonFlag) {
    buttonFlag = false;
    handle_button_press();
  }

  // Handle USBs
  if (Serial.available() > 0) { // Check if data is available to read
    //Serial.print("nothing");
    handle_usb_recieve(); 
  }
  //handle_get_tower_data();

  /*
  // If you want some actions to happen with a time delay, use this
  static unsigned long next_time = millis();
  if (millis() > next_time) {
    next_time += 2000;
    handle_ota_data();
  }
  */
  
}

