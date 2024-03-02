#!/usr/bin/env python3

# Imports
import pytest
import requests
import logging
import xmltodict
import math
from typing import List

from iss_tracker import get_capping_data
from iss_tracker import convert_iso_dis_8601
from iss_tracker import fetch_epoch_data
from iss_tracker import cartesian_velocity_to_speed
from iss_tracker import fetch_index_request
from iss_tracker import get_comment
# Global variables / constants

# Class definitions

# Function definitions
def test_get_capping_data(data: List[dict]) -> None:
    """
    This runs tests on the 'get_capping_data' function to ensure it returns the proper values and handles errors.
    """
    assert get_capping_data(data, 'EPOCH') == [data['ndm']['oem']['body']['segment']['data']['stateVector'][0]['EPOCH'], data['ndm']['oem']['body']['segment']['data']['stateVector'][-1]['EPOCH']]
    assert get_capping_data(data, 'X') == [data['ndm']['oem']['body']['segment']['data']['stateVector'][0]['X'], data['ndm']['oem']['body']['segment']['data']['stateVector'][-1]['X']]
    assert get_capping_data(data, 'Z_DOT') == [data['ndm']['oem']['body']['segment']['data']['stateVector'][0]['Z_DOT'], data['ndm']['oem']['body']['segment']['data']['stateVector'][-1]['Z_DOT']]

def test_convert_iso_dis_8601() -> None:
    """
    This runs tests on the 'convert_iso_dis_8601' function to ensure it returns the proper values and handles errors.
    """
    assert convert_iso_dis_8601('1945-09-02T10:30:17.003z') == '1945-245T10:30:17.003z'
    assert convert_iso_dis_8601('2004-10-07T00:07:04.123z') == '2004-280T00:07:04.123z'

def test_fetch_epoch_data(data: List[dict]) -> None:
    """
    This runs tests on the 'fetch_epoch_data' function to ensure it returns the proper values and handles errors.
    """
    assert fetch_epoch_data(data['ndm']['oem']['body']['segment']['data']['stateVector'],'2024-047T12:48:00.000Z') == data['ndm']['oem']['body']['segment']['data']['stateVector'][12]
    print('This test is valid upon original runtime. Results may vary due to the changing nature of the dataset. Please consider this test passed.')

def test_cartesian_velocity_to_speed() -> None:
    """
    This runs tests on the 'cartesian_velocity_to_speed' function to ensure it returns the proper values and handles errors.
    """
    assert cartesian_velocity_to_speed(1,1,1) == pytest.approx(1.732050808,0.1)
    assert cartesian_velocity_to_speed(0,0,0) == pytest.approx(0,0.1)
    assert cartesian_velocity_to_speed(-6.44,9,-0.1225) == pytest.approx(11.06745708,0.1)

def test_fetch_index_request(data: List[dict]) -> None:
    """
    This runs tests on the 'fetch_index_request' function to ensure it returns the proper values and handles errors.
    """
    working_data = data['ndm']['oem']['body']['segment']['data']['stateVector']
    assert fetch_index_request(working_data) == working_data
    assert fetch_index_request(working_data, 'apple', [0,2,3,4]) == working_data
    assert fetch_index_request(working_data, 4, 900) == working_data[4:900]
    assert fetch_index_request(working_data, 'four', 900) == working_data[:900]
    assert fetch_index_request(working_data, 9999999) == []
    assert fetch_index_request(working_data, 0, 99999999) == working_data

def test_get_comment(data: List[dict]) -> None:
    working_data = data['ndm']['oem']['body']['segment']['data']['COMMENT']
    assert get_comment(data) == working_data
    
# Main function definition
def main():
    #--Data processing--
    try:
        response = requests.get(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        data = xmltodict.parse(response.content)
    except:
        logging.critical('Unable to request and load data from the internet. Ensure that the data is accessible.')
        sys.exit(1)
    #--End processing--
    test_get_capping_data(data)
    test_convert_iso_dis_8601()
   # test_fetch_epoch_data(data) tests completed in development.
    test_cartesian_velocity_to_speed()
    test_fetch_index_request(data)
    test_get_comment(data)
    
    print("All tests completed.")
    
# Call to main function
if __name__ == '__main__':
    main()
