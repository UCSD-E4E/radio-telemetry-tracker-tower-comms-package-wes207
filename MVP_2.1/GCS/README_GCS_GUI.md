*********************************************************************
Title: 
GCS GUI - GCS (Ground Control Station)

Description: 
PyQT & Python source code, this utility software was developed to interact with LoRa device in the Ground Control Station, this station controls over the air and serial data traffic from the GCS to all the towers

Prerequisites: 
	PyQt, Python 3, code should be OS agnostic



Functions:

load_string_from_file()
    Loads the entire content of a text file into a single string.

    Args:
        filepath (str): The path to the text file.

    Returns:
        str: The content of the file as a string.  Returns an empty string
             if the file does not exist or an error occurs.


is_number()
	Determine if string is numeric


save_string_line()
	Saves string line into text file


build_cmd()
	Builds command based on tower number and delay


build_cmd_line()
	Builds command based on tower number and delay


breakdownfields()
	Separate fields from atring variable



class GGCCSS()
	This the main class of the program, 
	GGCCSS = Ground Control Station


class SRThread_GCS1()
	Setup indepent Thread and needed object events

def wait_for_newline()
	Received a whole string line of serial communication





*********************************************************************
