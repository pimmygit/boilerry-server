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
from Common import get_room_temperature, logger
from ConfigStore import ConfigStore
from Constants import FINER, CONST_TEMPERATURE_HISTORY
from Constants import CONST_THERMO_TEMPERATURE, CONST_THERMO_SWITCH, CONST_THERMO_STATE, CONST_TEMPERATURE_ROOM
from DS18B20 import DS18B20
from DatabaseDAO import DatabaseDAO
from GPIO import GPIO


class Thermostat:
    def __init__(self, dao: DatabaseDAO, gpio: GPIO, sensor: DS18B20):
        """
        Create object and initializes the values with what's currently defined in the database.
        This object will be refreshed on demand at various parts of the code, rather than periodically.
        Main purpose is to avoid quick repetitive calls to the database and sensors when we know
        nothing would have changed within the same request.

        Args:
            dao:    Database Access Object.
            gpio:   The RPi board pinout interface.
            sensor: The temperature sensor.
        Return:
            none
        Created:
            02.03.2024
        """
        self.CLASS = "Thermostat"
        self.config = ConfigStore()
        self.dao = dao
        self.gpio = gpio
        self.thermo_sensor = sensor

        logger(FINER, self.CLASS, "Initialising current state.")

        self.thermo_switch = self.config.getBoilerryServer(CONST_THERMO_SWITCH, "1")
        self.thermo_manual_temperature = self.dao.get_thermostat_manual()
        self.thermo_state = self.gpio.getRelaysState()
        self.temperature_room = get_room_temperature(self)
        self.temperature_history = self.dao.get_temperature_history(self.config.getSensor("sensor_1_id"))

    def get_thermo_switch(self):
        return self.thermo_switch

    def refresh_thermo_switch(self):
        logger(FINER, self.CLASS, "Updating: {}.".format(CONST_THERMO_SWITCH))
        self.thermo_switch = self.config.getBoilerryServer(CONST_THERMO_SWITCH, "1")

    def get_thermo_manual_temperature(self):
        return self.thermo_manual_temperature

    def refresh_thermo_manual_temperature(self):
        logger(FINER, self.CLASS, "Updating: {}.".format(CONST_THERMO_TEMPERATURE))
        self.thermo_manual_temperature = self.dao.get_thermostat_manual()

    def get_thermo_state(self):
        return self.thermo_state

    def refresh_thermo_state(self):
        logger(FINER, self.CLASS, "Updating: {}.".format(CONST_THERMO_STATE))
        self.thermo_state = self.gpio.getRelaysState()

    def get_room_temperature(self):
        return self.temperature_room

    def refresh_room_temperature(self):
        logger(FINER, self.CLASS, "Updating: {}.".format(CONST_TEMPERATURE_ROOM))
        self.temperature_room = get_room_temperature(self)

    def get_temperature_history(self):
        return self.temperature_history

    def refresh_temperature_history(self, start_period: str = None, end_period: str = None):
        logger(FINER, self.CLASS, "Updating: {}.".format(CONST_TEMPERATURE_HISTORY))
        self.temperature_history = self.dao.get_temperature_history(self.config.getSensor("sensor_1_id"), start_period, end_period)
