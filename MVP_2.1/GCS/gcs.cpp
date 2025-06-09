
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

#include <EEPROM.h>
#include <Preferences.h>

//Relay/ DOUT
const int DOUT1_PIN = 45;
const int DOUT2_PIN = 46;

// ADC
#include <esp_log.h>
#include <esp_adc_cal.h>
#include "driver/adc.h"
#define ADC_PIN ADC1_CHANNEL_0 
#define ADC_ATTENDB  ADC_ATTEN_DB_11 
#define ADC_UNIT     ADC_UNIT_1
#define VREF         3300  
static const char *TAG = "ADC_EXAMPLE";
uint32_t Vadc = 0;
// Function to initialize ADC
void adc_init() {
  // Configure ADC
  adc1_config_width(ADC_WIDTH_BIT_12);       // 12-bit resolution
  adc1_config_channel_atten(ADC_PIN, ADC_ATTENDB); // Set attenuation
}

// Function to read ADC and convert to voltage
uint32_t read_adc_voltage() {
  uint32_t adc_value = adc1_get_raw(ADC_PIN);
  // Convert ADC reading to voltage (mV)
  uint32_t voltage = (uint32_t)((float)adc_value * VREF / 4095.0);
  return voltage;
}

/*~~~~~ Instance Configuration ~~~~*/
// Device profile
#define DEVICE_ID       0x00 
#define FW_VER          0.32  
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
#define JN_LORA_CR   5     // 5-8 coding rate factor
#define JN_LORA_TX_POWER    22    // MAX = 22
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
  //~printf("ERROR!!! %s with error code %d\n", message, state);
  while(true); // loop forever
}

/*====== My globals =====*/
char extractedFields[4][128]; 
int numFields;
String tank_s, tank_rf;
int rx_delay = 0;
String SessionRx_Data_USBc  = "";
#define NO_ERROR      0
#define SYNTAX_ERROR  1

// SM
uint8_t SM = 0b00000000;
#define RLY  0x3
#define DOUT  0x2
typedef uint8_t ui;
struct ota{
  uint8_t id;
  uint8_t isgateway;
  uint8_t sf;
  uint8_t bw;
  uint8_t dl;
  uint8_t ul; 
};

ota OTA;
void rst(){
  //move everything into init state
  OTA.id = DEVICE_ID;
  OTA.isgateway = 1;
  OTA.bw = 125;
  OTA.sf = 7;
  OTA.dl = 11;
  OTA.ul = 10;
  //copy data from temporary variables into EEPROM(FLASH)

}

//set bit at bitNumber
void sb(ui *byte, ui bitNumber) {
  if (bitNumber < 8) {
    *byte |= (1 << bitNumber);
  }
}

//clear bit at bitNumber
void cb(ui *byte, ui bitNumber) {
  if (bitNumber < 8) {
    *byte &= ~(1 << bitNumber);
  }
}

//see if bit at bitNumber is a 1
bool tb(ui byte, ui bitNumber) {
  if (bitNumber < 8) {
    return (byte & (1 << bitNumber)) != 0;
  }
  return false;
}

// fill the array with Null
void fillCharArrayWithNullMemset(char arr[][128], int rows, int cols) {
  for (int i = 0; i < rows; ++i)
    memset(arr[i], '\0', cols * sizeof(char));
}

typedef enum {
  Q_IDN,
  Q_RSSI,
  Q_REC,
  CMD_ACK,
  CMD_RLY,
  Q_RLY,
  CMD_ID,
  Q_ID,
  CMD_DOUT,
  Q_DOUT,
  Q_ADC,
  CMD_RST,
  CMD_SF,
  Q_SF,
  Q_DL,
  Q_UL,
  CMD_DL,
  CMD_UL,
  CMD_UNKNOWN
} CommandType;

// Function to get command type from string
CommandType getCommandType(const char *command) {
  if (strcmp(command, "idn?"   ) == 0) return Q_IDN;
  if (strcmp(command, "rssi?" ) == 0) return Q_RSSI;
  if (strcmp(command, "rec?"   ) == 0) return Q_REC;
  if (strcmp(command, "ack"   ) == 0) return CMD_ACK;
  if (strcmp(command, "rly"  ) == 0) return CMD_RLY;
  if (strcmp(command, "rly?"  ) == 0) return Q_RLY;
  if (strcmp(command, "dout"  ) == 0) return CMD_DOUT;
  if (strcmp(command, "dout?"  ) == 0) return Q_DOUT;
  if (strcmp(command, "adc?"  ) == 0) return Q_ADC;
  if (strcmp(command, "rst"  ) == 0) return CMD_RST;
  if (strcmp(command, "id"  ) == 0) return CMD_ID;
  if (strcmp(command, "id?"  ) == 0) return Q_ID;
  if (strcmp(command, "sf"  ) == 0) return CMD_SF;
  if (strcmp(command, "sf?"  ) == 0) return Q_SF;
  if (strcmp(command, "dl?" ) == 0) return Q_DL;
  if (strcmp(command, "ul?") == 0) return Q_UL;
  if (strcmp(command, "dl" ) == 0) return CMD_DL;
  if (strcmp(command, "ul") == 0) return CMD_UL;
  return CMD_UNKNOWN;
}

/*====== CHANNEL SCANNING =====*/
int curr_channel = -1;
// max channel = 40
float chan_i_to_freq(int chan) {
  return 902.3 + 0.2*chan;
}

// Function to extract fields from a comma-delimited string
int extractFields(const char *inputString, char fields[][128], int maxFields) {
  fillCharArrayWithNullMemset(extractedFields, 4,128);
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

// increment the channel
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

//Switch radio to specified channel
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

//Transmit a String
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
  int16_t state = radio.begin(JN_INIT_FREQ, JN_LORA_BW, JN_LORA_SPREAD, JN_LORA_CR, 0x34, 0, 8);
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
  radio.setOutputPower(JN_LORA_TX_POWER)
  if (state != RADIOLIB_ERR_NONE) {
      error_message("CRC intialization failed", state);
  }
  Serial.println("Complete!");

  // ========== List boot info
  if(IS_GATEWAY) {
    String msg = "### Starting Ground Control Station (GCS) #"+String(DEVICE_ID)+", listening on uplink channel: "+String(CHANNEL_UPLINK)+"\n";
    Serial.print(msg);Tx_(msg);
    tune_to_rx();
  } else {
    String msg = "### Starting TOWER #"+String(DEVICE_ID)+", listening on downlink channel: "+String(CHANNEL_DOWNLINK)+"\n";
    Serial.print(msg);Tx_(msg);
    tune_to_rx();
  }

  // set the function that will be called when a new packet is received
  radio.setDio1Action(receiveISR);

  //Relay
    pinMode(DOUT1_PIN, OUTPUT);
    pinMode(DOUT2_PIN, OUTPUT);

  // start continuous reception
  Serial.print("Beginning continuous reception...");
  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    error_message("Starting reception failed", state);
  }
  Serial.println("Complete!");

  //OTA
  rst();
}

void parse_command(const char *command){
    switch (getCommandType(command)) {
      //Send information about Device id and FW version
      case Q_IDN:
        if (numFields>=3){
          rx_delay = atoi(extractedFields[2]);
          int device_id = atoi(extractedFields[1]);
          //~Serial.println("Executing CMD_IDN -> "+String(extractedFields[0])+","+String(extractedFields[1])+","+String(extractedFields[2]));
          if (device_id == DEVICE_ID)
            Serial.println(String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER)+", Uplink: "+String(CHANNEL_UPLINK)+ "/ Downlink: "+String(CHANNEL_DOWNLINK));
          else
            int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]) + "," + String(extractedFields[2]));
        }
        break;
      //Send acknowledgement
      case CMD_ACK:
          if (numFields==3){
            rx_delay = atoi(extractedFields[2]);
            int device_id = atoi(extractedFields[1]);
            //Serial.println("Executing CMD_ACK -> "+String(extractedFields[0])+","+String(extractedFields[1])+","+String(extractedFields[2]));
            int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));
            delay(rx_delay);
          }
          break;  
      //Send a query for the RSSI value
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
      //Send a query for a record
      case Q_REC:
          if (numFields>=3){
            rx_delay = atoi(extractedFields[2]);
            int device_id = atoi(extractedFields[1]);
            Serial.println("Executing Q_REC -> "+String(extractedFields[0])+","+String(extractedFields[1])+","+String(extractedFields[2]));
            int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]) + "," + String(extractedFields[2]));
          }
          break;
      //Send a query to toggle the relay
      case Q_RLY:
          if (numFields==3){
            int device_id = atoi(extractedFields[1]);
            rx_delay = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID){ 
              ui res = tb(SM, RLY);
              Serial.printf("%d\r\n",res);
            }
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));    
          }
          delay(rx_delay);
          break;
      
      case CMD_RLY:
          if (numFields==3){
            int device_id = atoi(extractedFields[1]);
            int stat = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID){
              if (stat == 1){
                digitalWrite(DOUT1_PIN, HIGH);
                sb(&SM, RLY);
              }
              else{
                digitalWrite(DOUT1_PIN, LOW);
                cb(&SM, RLY);
              }
              Serial.println("Rly set to: "+String(extractedFields[2]));
               //!!set status bit if the relay to remember the state of the relay  (1/0)
            }             
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));         
          }
          break;
      case Q_DOUT:
          if (numFields==3){
            int device_id = atoi(extractedFields[1]);
            rx_delay = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID){ 
              ui res = tb(SM, DOUT);
              //bool res = true;
              //Serial.printf("%d\r\n", res);  
              Serial.printf("%d\r\n",res);
            }
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));    
          }
          delay(rx_delay);
          break;
      case CMD_DOUT:
          if (numFields==3){
            int device_id = atoi(extractedFields[1]);
            int stat = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID){
              if (stat == 1){
                digitalWrite(DOUT2_PIN, HIGH);
                sb(&SM, DOUT);
              }
              else{
                digitalWrite(DOUT2_PIN, LOW);
                cb(&SM, DOUT);
              }                
              Serial.println("DOUT set to: "+String(extractedFields[2]));             
            }             
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));         
          }
          break;            
      case Q_ADC:
          if (numFields==3){
            int device_id = atoi(extractedFields[1]);
            rx_delay = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID){
              adc_init();
              // Print some information
              ESP_LOGI(TAG, "ADC Initialized");
              ESP_LOGI(TAG, "Reading ADC value from pin GPIO%d", ADC_PIN);

              // Read ADC and convert to voltage
              Vadc = read_adc_voltage();
              Serial.printf("%.3f\r\n");
            }
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));     
          }
          delay(rx_delay);
          break;
      case CMD_RST:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID){     
              Serial.println("Reset (re-initialize device): "+String(device_id));
              rst();//~ call for reinit function here and reset ST bitmap       
            }             
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ ",100");         
          }
          break;     
      case CMD_ID:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            int newValue = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID)
              OTA.id = (uint8_t)newValue;
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));         
          }
          break;
      case Q_ID:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println(String(OTA.id));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;               
      case CMD_SF:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            int newValue = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID)
              OTA.sf = (uint8_t)newValue;
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));         
          }
          break;
      case Q_SF:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println(String(OTA.sf));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;
      case Q_DL:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println(String(OTA.dl));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;
      case Q_UL:
          if (numFields>=2){
            int device_id = atoi(extractedFields[1]);
            if (device_id == DEVICE_ID)
              Serial.println(String(OTA.ul));
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1]));         
          }
          break;
      case CMD_DL:
          if (numFields>=3){
            int device_id = atoi(extractedFields[1]);
            int newValue = atoi(extractedFields[2]);
            if (device_id == DEVICE_ID)
              OTA.ul = (uint8_t)newValue;
            else
              int16_t res = Tx(String(extractedFields[0]) + "," + String(extractedFields[1])+ "," + String(extractedFields[2]));         
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
      default:
          Serial.print("Syntax error: ");
          String myString = String(command);
          Serial.println(myString);
          break;
  }
}

void handle_ota(){
    // you can receive data as an Arduino String
    String packet_data = "\0";
    delay(rx_delay);//Serial.printf("\r<delay: %d>\n", rx_delay);
    int state = radio.readData(packet_data);
    //tank_rf += packet_data;
    if (state == RADIOLIB_ERR_NONE) {
      Serial.println(packet_data);
      receivedFlag = false; //worked great!!, seems like the flag gets set multiple times during same transmision string
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

void handle_usb(){
    String receivedData = "";
    char c;

    //while there is serial data coming in. Stop the while loop when the character is a \n or \r which signals end of the cmd
    while (Serial.available() > 0) {
        c = Serial.read(); // Read a single character        
        if( c == '\n' ||  c == '\r' )
          break;
        receivedData += c;        
        delay(2); // Small delay to allow buffer to fill properly
    } 

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
          //just for debug
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
          //just for debug
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
          //just for debug
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

  // Handle Radio packet receptions
  if (receivedFlag) {
    receivedFlag = false;
    handle_ota();
    
  }

  // Handle button presses
  if (buttonFlag) {
    buttonFlag = false;

    String msg = String(DEVICE_TYPE)+", ID: "+String(DEVICE_ID)+", Firmware version: "+String(FW_VER)+", Channels: Uplink: "+String(CHANNEL_UPLINK)+ "/ Downlink: "+String(CHANNEL_DOWNLINK);   
    ///\int16_t state = Tx(msg);
    Serial.println(msg);
    Serial.println("Session USB-c data received:\n"+SessionRx_Data_USBc);
    SessionRx_Data_USBc="";
  }

  // Handle USBs
  if (Serial.available() > 0) { // Check if data is available to read
    handle_usb();
    //~     
  }
}
