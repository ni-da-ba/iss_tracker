#!/usr/bin/env python3

#imports
import xmltodict
import argparse
import logging
import socket
import sys
import requests
from typing import List
from datetime import datetime, timezone
import calendar
import math
from flask import Flask, request

#Global variables / constants
app = Flask(__name__)

#Class definitions

#Function definitions
def get_capping_data(a_list_of_dicts: List[dict], a_key_string: str) -> List[str]:
    """
    When fed the data in NASA's ISS data format, the function will find the top and bottom entries.
    These entries are considered the first and last portions of the data set.
    The function will then return those entries. This intended to find the epochs that the data set spans.

    Args: 
        a_list_of_dicts (List): A list of dictionaries. Dicts must have the same key set and follow ISS data structure.

        a_key_string (str): A key that appears in each dictionary associated with the desired value.
                      String type will be enforced.

    Returns: 
           capping_data (List): A list of the data in a given key 'capping' the top and bottom of the dataset.
    """
    try:
        capping_data = []
        capping_data.append(a_list_of_dicts['ndm']['oem']['body']['segment']['data']['stateVector'][0][a_key_string])
        capping_data.append(a_list_of_dicts['ndm']['oem']['body']['segment']['data']['stateVector'][-1][a_key_string])
        return(capping_data)
    except:
        logging.error('Unable to fetch capping data. Aborting operation.')
        pass

def convert_iso_dis_8601(standard_time: str) -> str:
    """
    When fed a set of temporal coordinates in ISO/DIS 8601 standard format, this function will convert
    that time into the equivalent of ISO/DIS 8601 modified format, which is what the ISS data set uses.

    Args:
        standard_time (str): A temporal coordinate in ISO/DIS 8601 standard format.

    Returns:
           converted_time (str): A set of temporal coordinates in ISO/DIS 8601 modified format.
    """
    try:
        time_split = standard_time.split('T')
        convert_sec = time_split[0].split('-')
        
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        month = int(convert_sec[1])

        days = sum(days_per_month[:month-1], int(convert_sec[2]))
        
        days_string = str(days)
        while len(days_string) < 3:
            days_string = "0" + days_string
        
        converted_time = convert_sec[0] + '-' + days_string + 'T' + time_split[1]
        return(converted_time)
    except:
        logging.error('Unable to convert time format. Aborting operation.')
        pass

def get_workable_time() -> str:
    """
    Uses datetime to get the current time at the running of the program.
    Converts that time into a format that will then be compared to the data.

    Returns:
           workable_time (str): The current time in ISS-workable ISO modified format.
    """
    try:
        current_time = datetime.now()
        
        iso_time = current_time.isoformat()
        
        workable_time = convert_iso_dis_8601(iso_time)
        return(workable_time)
    except:
        logging.error('Unable to get and convert current time. Aborting operation.')
        pass

def fetch_epoch_data(data: List[dict], epoch: str) -> List[dict]:
    """
    Takes an epoch as an argument and parses the ISS data set for the closest timestamp.
    Returns the associated contents of that timestamp as a List[dict].

    Args:
        epoch (str): The epoch to be fetched.
        data (List): The data containing epochs to be parsed.

    Returns:
           epoch_data (List): The associated data with the given epoch.
    """
    try:
        src_fragments = epoch.split(':')
        closeness = 77
        epoch_index = -1
        match_found = False
        for i, ele in enumerate(data):
            comp_fragments = data[i]['EPOCH'].split(':')
            if (src_fragments[0] == comp_fragments[0]):
                comp_closeness = abs(int(src_fragments[1]) - int(comp_fragments[1]))
                if (closeness > comp_closeness):
                    closeness = comp_closeness
                    epoch_index = i
                    match_found = True
        if (match_found==False):
            logging.error('Failed to fetch epoch data. Aborting Operation.')
            return([])
        return(data[epoch_index])
    except:
        logging.error('Failed to fetch epoch data. Aborting operation.')
        pass

def cartesian_velocity_to_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    """
    Takes velocity as a set of three cartesian values for the x, y, and z directions.
    Returns the resulting absolute speed.

    Args:
        x_dot (float): The cartesian velocity in the x direction.
        y_dot (float): The cartesian velocity in the y direction.
        z_dot (float): The cartesian velocity in the z direction.

    Returns:
           speed (float): The absolute speed.
    """
    try:
        return(math.sqrt(x_dot**2 + y_dot**2 + z_dot**2))
    except:
        logging.error('Unable to convert cartesian velocity. Aborting operation.')
        pass

def compute_average_speed(data: List[dict]) -> float:
    """
    Takes a list of dictionaries in the ISS format and returns the average speed
    across all timestamps in the list.

    Args:
        data (List): A list of dictionaries in ISS format.

    Returns:
           average_speed (float): The average speed across the entire list.
    """
    try:
        running_avg = 0
        avg_members = 0
        for i, ele in enumerate(data):
            try:
                x_dot = float(data[i]['X_DOT']['#text'])
                y_dot = float(data[i]['Y_DOT']['#text'])
                z_dot = float(data[i]['Z_DOT']['#text'])
                
                running_avg += cartesian_velocity_to_speed(x_dot,y_dot,z_dot)
                avg_members += 1
            except:
                logging.info('Encountered incomputable value while computing average. Omitting.')
                pass
        average = running_avg/avg_members
        return(average)
    except:
        logging.error('Unable to complete computation of averge speed. Aborting operation.')
        pass

def fetch_index_request(data: List[dict], offset=None, limit=None) -> List[dict]:
    """
    Takes a list of dictionaries in the ISS format. Also takes a variable 'limit' and 'offset.'
    By default, will return the entire list of dictionaries. Given optional arguments 
    'limit' and 'offset', will modify the data that is returned.

    Args:
        data (List): A list of dictionaries in the ISS format.
        limit (None): An optional modifier to the returned dataset. Will be taken as a string.
                      The modifier in question sets a limit of the index range that will be returned.
                      If an improper value or no value is supplied, defaults to the entire dataset.
        offset (None): An optional modifier to the returned dataset. Will be taken as a string.
                       The modifier in question sets a starting point from 0 of the returned data.
                       If an improper value is supplied or no value is supplied, defaults to 0.
    Returns:
           requested (List): A list of dictionaries from the data adhering to the arguments.
    """
    requested = []
    try:
        int_limit = int(limit)
    except:
        logging.info('Cannot convert limit to type: int. Disregarded.')
        int_limit = len(data)
    try:
        int_offset = int(offset)
    except:
        logging.info('Cannot convert offset to type: int. Disregarded.')
        int_offset = 0    
    for i in data[int_offset:int_limit]:
        requested.append(i)
    return(requested)

def get_data():
    #Typehinting seemed to break this function.
    """
    Accesses the ISS positional data from the internet, and formats it from XML into a dictionary.

    Returns:
           The ISS positional data from the internet, formatted into a dictionary.
    """
    try:
        response = requests.get(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        data = xmltodict.parse(response.content)
        return(data)
    except:
        logging.critical('Unable to request and load data from the internet. Ensure that the data is accessible.')
        sys.exit(1)

#Traditional typehinting does not seem to work with flask routes. I have tried to
#offset this by defining almost all the functionality of these routes elsewhere.
        
@app.route('/epochs', methods=['GET'])
def index_request():
    """
    Takes input from an incoming request for offset and limit values. Then, takes these numbers
    and uses them to curate a portion of the dataset as requested before returning it.

    Returns:
           result (List): The curated portion of the dataset.
    """
    data = get_data()
    working_data = data['ndm']['oem']['body']['segment']['data']['stateVector']
    offset = request.args.get('offset')
    limit = request.args.get('limit')

    result = fetch_index_request(working_data, offset, limit)
    return(result)

@app.route('/epochs/<epoch>', methods=['GET'])
def epoch_request(epoch):
    """
    Takes input from an incoming request, comparing the  value to the dataset.
    Once identifying the closest epoch to the one provided (if formatting is correct),
    its data will be returned.

    Returns:
           result (List): The associated data with the epoch closest to the one requested by the user.
    """
    data = get_data()
    working_data = data['ndm']['oem']['body']['segment']['data']['stateVector']

    result = fetch_epoch_data(working_data, epoch)

    if(result==[]):
        return("Encountered invalid epoch. Operation aborted.\n")
    return(result)

@app.route('/epochs/<epoch>/speed', methods=['GET'])
def speed_request(epoch):
    """
    Takes an input from an incoming request, comparing the value to the dataset.
    Once identifying the closest epoch to the one provided, if the formatting is correct,
    its speed will be calcualted, and then returned.

    Returns:
           result (string): The speed of the station at the requested epoch.
    """
    data = get_data()
    working_data = data['ndm']['oem']['body']['segment']['data']['stateVector']

    epoch_request = fetch_epoch_data(working_data, epoch)
    if(epoch_request==[]):
        return("Encountered invalid epoch. Operation aborted.\n")
    
    x_dot = float(epoch_request['X_DOT']['#text'])
    y_dot = float(epoch_request['Y_DOT']['#text'])
    z_dot = float(epoch_request['Z_DOT']['#text'])
    result = cartesian_velocity_to_speed(x_dot,y_dot,z_dot)
    return(str(result)+' km/s\n')

@app.route('/now', methods=['GET'])
def now_request():
    """
    Calculates an epoch that would be considered closest to the time at which the program is run.
    Returns the associated data with that epoch, as well as calculating its speed and returning it.

    Returns:
           result (List): The associated data with the current epoch, along with its speed.
    """
    data = get_data()
    working_data = data['ndm']['oem']['body']['segment']['data']['stateVector']

    current_epoch = get_workable_time()

    epoch_matched = fetch_epoch_data(working_data, current_epoch)

    x_dot = float(epoch_matched['X_DOT']['#text'])
    y_dot = float(epoch_matched['Y_DOT']['#text'])
    z_dot = float(epoch_matched['Z_DOT']['#text'])
    current_speed = cartesian_velocity_to_speed(x_dot,y_dot,z_dot)

    speed_data = {"SPEED": {"#text": current_speed, "@units": "km/s"}}
    
    result = [epoch_matched, speed_data]    
    return(result)

#Main function definition
def main():
    #--Parsing commandline args--
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--loglevel', type=str, required=False, default='WARNING',
                            help='set log level to DEBUG, INFO, WARNING, ERROR, or CRITICAL')
    args = parser.parse_args()
    
    format_str=f'[%(asctime)s {socket.gethostname()}] %(filename)s:%(funcName)s:%(lineno)s - %(levelname)s: %(message)s'
    
    logging.basicConfig(level=args.loglevel, format=format_str)
    #--End parsing--

    #--Begin running--
    app.run(debug=True, host='0.0.0.0')
    #--End running--
    
#Call to main function
if __name__ == '__main__':
    main()
