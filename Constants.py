#!/usr/bin/python

"""
Application constants - do not change.
Configuration settings are stores in boilerry.ini
"""
APP_NAME = "boilerry"

"""
Database settings are intentionally hardcoded here as they will only change
if we are migrating to another database server type. The user has no valid reason
to change the database settings.
"""
DB_TYPE = "MySQL"
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "boilerry"
DB_USER = "boser"
DB_PASS = "S1r3n3"

CRITICAL = 0
WARNING = 1
INFO = 2
FINE = 3
FINER = 4
FINEST = 5

# Location where the log should be directed to. Two fixed values: [file|stdout]
LOG_SINK = "file"
LOG_LEVELS = ["CRITICAL", "WARNING", "INFO", "FINE", "FINER", "FINEST"]

# Frequency with which the settings will be re-read from the file and database
CONFIG_UPDATE_PERIOD = 60

# HEATING_STATE_ON    -> GPIO_PIN_RELAY_1[1] && GPIO_PIN_RELAY_2[1]
HEATING_STATE_ON = True
# HEATING_MODE_OFF   -> GPIO_PIN_RELAY_1[0] && GPIO_PIN_RELAY_2[1]
HEATING_STATE_OFF = False

# Operating mode of the heating system
HEATING_MODE_MANUAL = 1
HEATING_MODE_TIMED = 2
HEATING_MODE_AUTO = 3

# Thermostat
CONST_THERMO_STATE = "thermo_state"
CONST_THERMO_SWITCH = "thermo_switch"
CONST_THERMO_RELAY = "thermo_relay"
CONST_THERMO_TEMPERATURE = "thermo_temperature"

# Temperature sensor
CONST_TEMP_RECORD_INTERVAL = "temp_record_interval"
CONST_TEMP_NOW = "temp_now"
CONST_TEMP_HISTORY = "temp_history"
CONST_TEMP_UNITS = "temp_units"
