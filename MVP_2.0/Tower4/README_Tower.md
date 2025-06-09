*********************************************************************
Title: 
LoRa ESP32 Tower (Applies to any tower number)

Description: 
Firmware source code for Tower LoRa device, this station controls over the air and serial data traffic from the GCS to all the towers

Prerequisites: 
	VSCode, with PlatformIO, code should be OS agnostic



Functions:

adc_init
	Function to initialize & Configure

read_adc_voltage
	Read Voltage, with scale formula, this readback from ADC pin

receiveISR(void)
	Callback function when receiving data

buttonISR(void) 
	Callback function when button pressed

error_message
	Helper function foor error messaging

rst
	Move parameters into a init state

sb
	Set bit in a mask

cb
	Clear bit in a mask

tb
	Test bit in a word variable

fillCharArrayWithNullMemset
	Initialize data array object

chan_i_to_freq
	Returns frequency float value 

extractFields
	Breakdown of fields in a given string

advance_channel
	Move to next next channel in the spectrum

tune_to_channel
	tune to specific frequency, per desired channel

tune_to_tx
	Get ready to transmit

tune_to_rx
	Get ready to receive

Tx
	Transmit given string of characters, but tune first

Tx_
	Transmit given string of characters

setup
	Initial setup for the LoRa device

parse_ota_command
	Take OTA received messages and handle them per semantic meaning

parse_s_command
	Take serial received messages and handle them per semantic meaning

loop
	Continuous closed loop of the processor's execution

*********************************************************************
