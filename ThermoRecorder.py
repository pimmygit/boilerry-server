#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# v.1.0.0 | 04.02.2018
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
import time
import threading

from Constants                   import *
from Common                   import *

from DS18B20                  import DS18B20
from DatabaseDAO              import DatabaseDAO

###################################################################
# Provides mechanism to periodically record the sensor's reading in the database.
# -----------------------------------------------------------------
# 1.0.0. | 04.02.2018 - First version
class ThermoRecorder(threading.Thread):

  ################################################################################  
  # Name:     __init__(Integer, Integer)
  # Desc:     Initialise and start the thread which probes and stores the temperature.
  # Param:    sensor_id        -> Type: String, Value: Id of the sensor
  # Return:   none
  # Modified: 04.02.2018
  def __init__(self, sensor_id):
    
    global DB_HOST
    global DB_PORT
    global DB_NAME
    global DB_USER
    global DB_PASS
    
    threading.Thread.__init__(self)
    
    self.CLASS             = "ThermoRecorder"
    self.thermo_sensor     = DS18B20()
    self.dao               = DatabaseDAO(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS)
    
    self.sensor_id         = sensor_id
    
    # Set some defaults
    self.running           = True
    self.units             = 'C'
    self.timeout           = 30
    self.period            = 600
    
  # EndOfFunction - __init__
  ################################################################################
  
  
  ################################################################################  
  # Name:     run()
  # Desc:     The constantly looping thread recording the read temperature in the database
  # Param:    none
  # Return:   none
  # Modified: 04.02.2018
  def run(self):
    while self.running:
      self.setConfig()
            
      logger(LOG_SINK, FINE, self.CLASS, "Periodic temperature recording: sensor[{}], units[{}], timeout[{}], period[{}]."
        .format(self.sensor_id, self.units, self.timeout, self.period))
      self.dao.save_temperature(self.sensor_id, self.units, self.thermo_sensor.getTemp(self.sensor_id, self.units, self.timeout))
      
      # Check every second if we have to terminate
      # (we do not want to wait the entire sleep time to terminate)
      sleep_period         = self.period

      while sleep_period > 0:
        #logger(LOG_SINK, FINEST, self.CLASS, "Sleeper count: {}.".format(sleep_period))
        if not self.running:
          self.dao.close()
          logger(LOG_SINK, FINER, self.CLASS, "Temperature recorder stopped.")
          break
        sleep_period -= 1
        time.sleep(1)
  # EndOfFunction - run()
  ################################################################################
      

  ################################################################################
  # Name:     setPeriod()
  # Desc:     Sets the time in seconds on how often to check and record the temperature
  # Param:    none
  # Return:   none
  # Modified: 04.02.2018
  def setConfig(self):
    thermo_units          = self.dao.get_property("thermoUnits")
    thermo_period         = int(self.dao.get_property("thermoPeriod"))
    thermo_timeout        = int(self.dao.get_property("thermoTimeout"))
    
    logger(LOG_SINK, FINEST, self.CLASS, "Checking for any config changes..")
    
    if (self.units != thermo_units):
      logger(LOG_SINK, INFO, self.CLASS, "Property 'thermoUnits' modified to: {}.".format(thermo_units))
      self.units             = thermo_units
    if (self.period != thermo_period):
      logger(LOG_SINK, INFO, self.CLASS, "Property 'thermoPeriod' modified to: {}.".format(thermo_period))
      self.period             = thermo_period
    if (self.timeout != thermo_timeout):
      logger(LOG_SINK, INFO, self.CLASS, "Property 'thermoTimeout' modified to: {}.".format(thermo_timeout))
      self.timeout             = thermo_timeout
  # EndOfFunction - setPeriod()
  ################################################################################


  ################################################################################
  # Name:     stop
  # Desc:     Terminates the temperature recorder
  # Param:    none
  # Return:   none
  # Modified: 04.02.2018
  def stop(self):
    logger(LOG_SINK, FINER, self.CLASS, "Stopping temperature recorder..")
    self.running           = False
  # EndOfFunction - stop()
  ################################################################################
