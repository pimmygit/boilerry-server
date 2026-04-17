#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# v.1.0.0 | 31.01.2018
#
# (C) Copyright VAYAK Ltd (info@vayak.com). 2018  
# All Rights Reserved
#
# THIS IS UNPUBLISHED PROPRIETARY SOURCE CODE
# The copyright notice above does not evidence any
# actual or intended publication of such source code.
#
# RESTRICTED RIGHTS:
# This file may have been supplied under a license.
# It may be used, disclosed, and/or copied only as permitted
# under such license agreement. Any copy must contain the
# above copyright notice and this restricted rights notice.
# Use, copying, and/or disclosure of the file is strictly
# prohibited unless otherwise provided in the license agreement.
###################################################################
import asyncio
import sched
import sys
import time

from AndroidServer import AndroidServer
from Common import logger
from ConfigStore import ConfigStore
from Constants import INFO, CRITICAL
from DatabaseDAO import DatabaseDAO
from DS18B20 import DS18B20
from GPIO import GPIO
from ThermoControl import ThermoControl
from WeatherDAO import WeatherDAO

config = ConfigStore()
dao_db = DatabaseDAO()
gpio = GPIO()
sensor = DS18B20()

# Start motion recording
#motion_recorder = MotionRecorder(GPIO_PIN_PIR)
#motion_recorder.start()

# Start periodic retrieval of the outside weather data for faster processing
dao_hw = WeatherDAO(
    config.getMetStation("latitude"),
    config.getMetStation("longitude"),
    config.getMetStation("unit_speed"),
    config.getMetStation("unit_temperature"),
    config.getMetStation("min_days_history")
)

time_to_execute_prop = config.getMetStation("time_to_retrieve_weather_history")
logger(INFO, "Boilerry", "Starting daily weather data collection for latitude[{}] and longitude[{}] at '{}' o'clock.".format(
    ConfigStore.getMetStation(ConfigStore(), "latitude"),
    ConfigStore.getMetStation(ConfigStore(), "longitude"),
    time_to_execute_prop))
if time_to_execute_prop:
    # Set up scheduler
    s = sched.scheduler(time.localtime, time.sleep)
    # Schedule when you want the action to occur
    time_to_execute = time.strptime(time_to_execute_prop, '%H:%M:%S')
    s.enterabs(time_to_execute, 0, dao_hw.retrieve_and_store_weather_history)
    # Block until the action has been run
    s.run()
else:
    logger(INFO, "Boilerry", "Missing 'time_to_retrieve_weather_history' property prevents from periodic weather retrieval.")

# Start the thermostat control
try:
    thermostat = ThermoControl(dao_db, gpio, sensor)
    thermostat.start()
except Exception as e:
    logger(CRITICAL, "Boilerry", "Failed to start the Thermostat controller: {}. Exiting..".format(e))
    #motion_recorder.stop()
    #thermo_recorder.stop()
    sys.exit(1)

# Start Android server
server = AndroidServer(dao_db, gpio, sensor)
asyncio.run(server.main())
