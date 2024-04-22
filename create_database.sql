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
# Name: weather
# Desc: Contains the weather summary for a given datetime
# Last: 18.04.2024
#
CREATE TABLE IF NOT EXISTS weather(
datetime		    TIMESTAMP NOT NULL DEFAULT NOW(),	# Date and time when the measurement was taken
unit_speed          VARCHAR(3) NOT NULL DEFAULT 'mph',	# Wind speed unit - kph/mph
unit_temperature    VARCHAR(1) NOT NULL DEFAULT 'C',	# Temperature unit - C/F
temperature		    FLOAT,					            # Measured temperature
windchill   	    FLOAT,   					        # Windchill
wspd                FLOAT                               # Wind speed
);
#
# Name: temperature
# Desc: Contains temperature measurements
# Last: 21.01.2018
#
CREATE TABLE IF NOT EXISTS temperature(
sensor			VARCHAR(20) NOT NULL,			    # ID of the sensor
datetime		TIMESTAMP NOT NULL DEFAULT NOW(),	# Time when the measurement was taken
unit			VARCHAR(1) NOT NULL DEFAULT 'C',	# Measurement unit - C/F
temperature		FLOAT,					            # Measured temperature
thermo_state	TINYINT(1)					        # Is the boiler heating element On/Off - 0/1
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
sensor			VARCHAR(20) NOT NULL,		        # ID of the sensor
datetimeFirst		TIMESTAMP,				        # Time when the first motion was detected
datetimeLast		TIMESTAMP				        # Time when the measurement was taken
);
