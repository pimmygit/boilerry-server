#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# (C) Copyright VAYAK Ltd (info@vayak.com). 2024
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
import threading
from time import sleep

from Common import *
from DS18B20 import DS18B20
from DatabaseDAO import DatabaseDAO
from GPIO import GPIO


class ThermoControl(threading.Thread):
    """
    Periodically checks the Boilerry settings as stored in the database and
    sets the state of the boiler according the them and the detected environment (time, room temperature, etc.)
    --------------------------------------------
    1.0.0. | 03/02.1024 - Class created

    TODO:   1.) Check for overlapping time periods before adding to the list.
            2.) Upon adding, re-order the list by time period.
    """

    def __init__(self, dao: DatabaseDAO, gpio: GPIO, sensor: DS18B20):
        """
        Create object and initialize

        Args:
            dao:    Database Access Object: MySQL database
            gpio:   The interface to external peripheral
            sensor: USB temperature sensor

        Returns:    none
        Modified:   [10/Dec/2023, 24/Mar/2024]
        """
        super().__init__()
        self.CLASS = "ThermoControl"
        self.config = ConfigStore()
        self.dao = dao
        self.gpio = gpio
        self.thermo_sensor = sensor

        self.running = True
        self.THERMOSTATS = []

    def run(self):
        """
        Thread to perform the periodic operations to set the boiler state according the settings stored in the database.
        """
        logger(FINE, self.CLASS, "Starting thermostat temperature control..")

        while self.running:
            logger(FINEST, self.CLASS, "Checking ThermoSwitch state..")
            thermo_switch = int(self.config.getBoilerryServer(CONST_THERMO_SWITCH, 1))

            logger(FINEST, self.CLASS, "Determining the 'Heating state' according to settings & environment..")

            if thermo_switch == 2:
                'Do the timer magic'

            'Maintain the Always ON temperature'
            if thermo_switch == 1:
                thermo_temperature = self.dao.get_thermostat_manual()
                room_temperature = get_temperature_now(self)
                self.gpio.temperature_to_relay_state(thermo_temperature, room_temperature)

            'Force switch off the heating'
            if thermo_switch == 0:
                logger(FINE, self.CLASS, "Thermostat  OFF")
                self.gpio.setRelayState(HEATING_STATE_OFF)
                # self.stop()

            '''
            Make a record of the current temperature (if its time to do that).
            For better presentation, the time when the temperature measurement it taken, is on the top of the hour,
            divided by the period specified in the property.
            '''
            try:
                thermo_record_interval = int(self.config.getBoilerryServer(CONST_TEMP_RECORD_INTERVAL, "10"))
            except ValueError:
                thermo_record_interval = 10
                logger(FINEST, self.CLASS, "Temperature recording property '{}' is not an integer: {}.".format(
                    CONST_TEMP_RECORD_INTERVAL, self.config.getBoilerryServer(CONST_TEMP_RECORD_INTERVAL, "10")
                ))

            # Let's do some checks and let the user know if the settings look abnormal
            if thermo_record_interval <= 0:
                logger(FINEST, self.CLASS, "Recording temperature is OFF.")
            elif getCurrentTimeMinutes() % thermo_record_interval == 0:
                logger(FINEST, self.CLASS, "Recording temperature current_minutes[{}], interval[{}].".format(
                    getCurrentTimeMinutes(), self.config.getBoilerryServer(CONST_TEMP_RECORD_INTERVAL, "10")
                ))
                sensor = "sensor_1"
                self.dao.save_temperature(
                    sensor,
                    self.config.getBoilerryServer(CONST_TEMP_UNITS, "C"),
                    self.thermo_sensor.getTemp(
                        self.config.getSensor(sensor + "_id"),
                        int(self.config.getSensor(sensor + "_timeout")),
                        self.config.getBoilerryServer(CONST_TEMP_UNITS, "C"),
                    )
                )

            sleep(60)

    def stop(self):
        """
        Terminates the temperature control
        Args:       none
        Returns:    none
        """
        logger(FINER, self.CLASS, "Stopping thermostat temperature control..")
        self.running = False
