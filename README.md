# ISS Tracker - Nicholas Darwin Babineaux
## Project Overview
This project is a flask application that, once deployed, allows the user to query various types of information about the whereabouts of the International Space Station. Some examples of this are its position in both cartesian and geodesic coordinates, cartesian velocities, its absolute speed, and whatever region on Earth that it may be passing over at a given time. This is achieved by accessing the publically-available ISS positional database and processing its information.

The data can be found in XML format at: 

```https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml```.
## File Overviews
### ```iss_tracker.py```
This is this primary script containing all functionality, flask routes, and setup for the entire program. It is the file being accessed when building and running the overall program.
### ```test_iss_tracker.py```
This is the unit testing script for the program. The flask routes themselves have not been unit tested, but they are designed to basically be extensions of non-flask functionality, all of which is thoroughly tested in this program.
### ```README.md```
A file that will give anybody perusing the repository a solid idea of the project, how to run the program, and how it is structured. You are here.
### ```Dockerfile```
A file that is necessary for the functionality of the program as a containerized application using Docker but not of great import to the user. Contains instructions on how the application is to be built and deployed using Docker.
### ```docker-compose.yml```
A yaml file that contains the second half of the deployment process with Docker. This automates the commands that are usually required to run a containerized program with Docker, making the entire process much easier on the user. 
### ```diagram.png```
A software diagram that is intended to clarify the overall file and software structure of the project. Contains visual aids that may clarify points of confusion. 
## Usage
You may pull this software into a valid directory from Docker Hub using the command as follows: 
```
docker pull nidaba936/iss_tracker:1.0
```


With the container in your possession, you may proceed:

#### ```test_iss_tracker.py```:

You may run the unit tests with the command: 

```
docker run --rm nidaba936/iss_tracker:1.0 test_iss_tracker.py
```

You will receive an output that is similar to:
```
All tests completed.
```
Indicating that all tests have been completed without issue.

#### ```iss_tracker.py```

First, you must deploy the application with the command:
```
docker-compose up -d
```

Then, you may access the functionality of the program with the basis:
```
curl 'localhost:5000/'
```
After the `5000` but before the ```'```:

`/epochs`: Returns the entire dataset in dictionary format

`/header`: Returns the header of the data set.

`/comment`: Returns the comments of the data set.

`/metadata`: Returns the metadata of the data set.

`/epochs?limit=int&offset=int`: Returns modified list of epochs given query parameters
```
limit and offset indices start at max, 0, leave empty for defaults.
The data that is returned to you will be BETWEEN the INTEGER indices of 'offset' and 'limit'

```

`/epochs/<epoch>`: Returns state vectors for a specific epoch from the data set
    
    epoch must be provided in format: YEAR-DAYTHR:MI:SE.MIL

`/epochs/<epoch>/speed`: Returns instantaneous speed for a specific epoch in the data set
```
epoch must be provided in format: YEAR-DAYTHR:MI:SE.MIL
```

`/epochs/<epoch>/location`: Returns locational data for a specific epoch in the data set
```
epoch must be provided in format: YEAR-DAYTHR:MI:SE.MIL
```

`/now`: Returns state vectors, locational data, and instantaneous speed for the epoch  that is nearest in time

When you are finished with the program, you may stop the program with:
```
docker-compose down
```
#### Sample Output

All output will appear in the form of some list of data, except for `/epochs/<epoch>/speed`, which will simply provide a speed value.

For instance, at some runtime, the result of the `/now` route was:

```
{
  "ALTITUDE": {
    "#text": 414.9086849816373,
    "@units": "km"
  },
  "EPOCH": "2024-069T02:26:30.000Z",
  "GEOLOCATION": {
    "ISO3166-2-lvl4": "MX-YUC",
    "country": "Mexico",
    "country_code": "mx",
    "county": "Tahmek",
    "locality": "San Francisco",
    "state": "Yucat\u00e1n"
  },
  "LATITUDE": {
    "#text": 20.873190044190952,
    "@units": "deg"
  },
  "LONGITUDE": {
    "#text": -89.2409172937796,
    "@units": "deg"
  },
  "SPEED": {
    "#text": 7.666890088703673,
    "@units": "km/s"
  },
  "X": {
    "#text": "-2018.1368447422999",
    "@units": "km"
  },
  "X_DOT": {
    "#text": "-4.1603832442146498",
    "@units": "km/s"
  },
  "Y": {
    "#text": "6018.71000188982",
    "@units": "km"
  },
  "Y_DOT": {
    "#text": "-3.55181061949399",
    "@units": "km/s"
  },
  "Z": {
    "#text": "2410.6230405154602",
    "@units": "km"
  },
  "Z_DOT": {
    "#text": "5.3718764148824496",
    "@units": "km/s"
  }
}
```
Going down the list of data, you will find the altitude of the station and its units, the epoch at which this data was recorded, the region of the world over which the station is located, the latitude of the station and its units, and so on, so forth. All data outputted by this program has units and labels included such that it is easy to read and understand.
## Diagram
![diagram](https://github.com/ni-da-ba/iss_tracker/assets/142941255/04bbbea3-6990-47cd-a2fe-9fa87c4ce8e9)

The user of the program will pull this container from a registry of images and then activate the program. When queries are supplied to the ongoing flask application through the ports, a request is sent to the ISS website on the internet, the reply to which is the data set that will be worked on.

According to the query of the user, some work is done upon the data, and then the requested results are sent to screen. After this point, the user will visually receive their requested data, and will be able to continue sending queries until they choose to shut off the program.

## Credits
The code within these files is almost entirely of my own creation. Limited inspiration has been taken from the university. Credit should be so dealt firstly to me, and secondly to the university.
## Further Questions
If you have any further questions or run into issues with the project that you cannot seem to figure out yourself, you may contact the curator of this repo (me) and I will respond promptly.
