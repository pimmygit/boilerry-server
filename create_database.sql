USE boilerry;
#
# Name: users
# Desc: Contains user accounts
# Last: 21.01.2018
#
CREATE TABLE IF NOT EXISTS user(
name			VARCHAR(20) NOT NULL,			    # Login name
title			VARCHAR(5),				            # Users title
nameFirst		VARCHAR(20) NOT NULL,			    # Users first name
nameLast		VARCHAR(20) NOT NULL,			    # Users last name
dob			    DATE,					            # Date of birth
mail			VARCHAR(50) NOT NULL PRIMARY KEY,	# Identification of the user
addressLine1	VARCHAR(30),				        # First line address
addressLine2	VARCHAR(30),				        # Second line address
addressTown		VARCHAR(20),				        # Town
addressCode		VARCHAR(10),				        # Post Code
addressCountry	VARCHAR(20),				        # Country
phone			VARCHAR(20),				        # Contact landline number
password		VARCHAR(20),				        # Password for account access
created			TIMESTAMP NOT NULL DEFAULT NOW(),	# Time of account creation
modified		TIMESTAMP				            # Time of account's last modification
);
#
# Name: temperature
# Desc: Contains temperature measurements
# Last: 03.06.2024
#
CREATE TABLE IF NOT EXISTS temperature(
datetime		    TIMESTAMP NOT NULL DEFAULT NOW(),	# Date and time when the measurement was taken
time_state_on       SMALLINT NOT NULL DEFAULT 0,        # Shows the time in seconds for the interval between this and the previous reading, for which the boiler was heating.
unit_speed          VARCHAR(3) NOT NULL DEFAULT 'mph',	# Wind speed unit - kph/mph
unit_temperature    VARCHAR(1) NOT NULL DEFAULT 'C',	# Temperature unit - C/F
temperature		    FLOAT,                              # Measured temperature outside
windchill   	    FLOAT,                              # Windchill
wspd                FLOAT,                              # Wind speed
sensor_1            FLOAT,                              # Measured temperature for the given sensor
sensor_2            FLOAT,                              # Measured temperature for the given sensor
sensor_3            FLOAT                               # Measured temperature for the given sensor
);
#
# Name: thermostat
# Desc: Contains the temperature which the boiler should maintain
# Last: 10.12.2023
#
CREATE TABLE IF NOT EXISTS thermostat(
temperature		FLOAT,					            # Temperature to maintain during this period
timeStart		VARCHAR(5) NOT NULL,	            # Start of the time period in the format: "HH:MM"
timeEnd 		VARCHAR(5) NOT NULL,	            # End of the time period in the format: "HH:MM"
);
#
# Name: presence
# Desc: Contains detection of presence. First and last motion is determined by the settings.presenceInterval value.
# Last: 21.01.2018
#
CREATE TABLE IF NOT EXISTS presence(
sensor			    VARCHAR(20) NOT NULL,           # ID of the sensor
datetimeFirst		TIMESTAMP,				        # Time when the first motion was detected
datetimeLast		TIMESTAMP				        # Time when the measurement was taken
);
