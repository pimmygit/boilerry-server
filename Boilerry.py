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
import sys

from Constants import CRITICAL
from DatabaseDAO import DatabaseDAO
from ConfigStore import ConfigStore
from Common import logger
from DS18B20 import DS18B20
from GPIO import GPIO
from ThermoControl import ThermoControl
from AndroidServer import AndroidServer

dao = DatabaseDAO()
config = ConfigStore()
gpio = GPIO()
sensor = DS18B20()

# Start motion recording
#motion_recorder = MotionRecorder(GPIO_PIN_PIR)
#motion_recorder.start()

# Start the thermostat control
try:
    thermostat = ThermoControl(dao, gpio, sensor)
    thermostat.start()
except Exception as e:
    logger(CRITICAL, "Boilerry", "Failed to start the Thermostat controller: {}. Exiting..".format(e))
    #motion_recorder.stop()
    #thermo_recorder.stop()
    sys.exit(1)

# Start Android server
AndroidServer(dao, gpio, sensor)
