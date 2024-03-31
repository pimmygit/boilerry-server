#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
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
import RPi.GPIO as RPIGPIO

from Common import logger
from ConfigStore import ConfigStore
from Constants import WARNING, FINE, FINER, HEATING_STATE_OFF, HEATING_STATE_ON


class GPIO:
    """
    Provides interface to relay switches

    Created: 24.02.2018
    """
    def __init__(self):
        """
        Initialise the RPI board IO GPIO.

        Created: 24.02.2018
        """
        self.CLASS = "GPIO"

        self.config = ConfigStore()

        # Configure the RPi board IO
        # ===========
        RPIGPIO.setmode(RPIGPIO.BOARD)
        RPIGPIO.setwarnings(False)
        RPIGPIO.setup(self.config.getGpioPin("relay_1"), RPIGPIO.OUT)
        RPIGPIO.setup(self.config.getGpioPin("relay_2"), RPIGPIO.OUT)

    def getRelaysState(self) -> bool:
        """
        Function to read the state of the relays and determine the state:
            HEATING_MODE_ON    -> GPIO_PIN_RELAY_1[1]
            HEATING_MODE_OFF   -> GPIO_PIN_RELAY_1[0] && GPIO_PIN_RELAY_2[1]
        Returns:
            Determine if the heating is ON or OFF, based on the state of the relay switches
        Created:
            24.02.2018
        """
        relay_state_1 = int(RPIGPIO.input(self.config.getGpioPin("relay_1")))
        relay_state_2 = int(RPIGPIO.input(self.config.getGpioPin("relay_2")))

        if relay_state_1 == 0 and relay_state_2 == 1:
            logger(FINER, self.CLASS,
                   "Heating state is {} due to relay state of: relay_1[{}]->{}, relay_2[{}]->{}"
                   .format(HEATING_STATE_OFF,
                           self.config.getGpioPin("relay_1"), relay_state_1,
                           self.config.getGpioPin("relay_2"), relay_state_2))
            return bool(HEATING_STATE_OFF)
        else:
            logger(FINER, self.CLASS,
                   "Heating state is {} due to relay state of: relay_1[{}]->{}, relay_2[{}]->{}"
                   .format(HEATING_STATE_ON,
                           self.config.getGpioPin("relay_1"), relay_state_1,
                           self.config.getGpioPin("relay_2"), relay_state_2))
            return bool(HEATING_STATE_ON)

    def setRelaysState(self, state: int):
        """
        Function to set the state of the relays:
            HEATING_MODE_ON    -> GPIO_PIN_RELAY_1[1]
            HEATING_MODE_OFF   -> GPIO_PIN_RELAY_1[0] && GPIO_PIN_RELAY_2[1]
        Args:
            state:  Value: HEATING_MODE_ON | HEATING_MODE_OFF
        Returns:
            none
        Config:
            24.02.2018
        """
        if str(state).lower() == str(HEATING_STATE_OFF).lower():
            logger(FINER, self.CLASS,
                   "Switching heating to {}, relay switches: relay_1[{}]->{}, relay_2[{}]->{}"
                   .format(HEATING_STATE_OFF,
                           self.config.getGpioPin("relay_1"), 0,
                           self.config.getGpioPin("relay_2"), 1))
            RPIGPIO.output(self.config.getGpioPin("relay_1"), RPIGPIO.LOW)
            RPIGPIO.output(self.config.getGpioPin("relay_2"), RPIGPIO.HIGH)
        else:
            logger(FINER, self.CLASS,
                   "Switching heating to {}, relay switches: relay_1[{}]->{}, relay_2[{}]->{}"
                   .format(HEATING_STATE_ON,
                           self.config.getGpioPin("relay_1"), 1,
                           self.config.getGpioPin("relay_2"), 1))
            RPIGPIO.output(self.config.getGpioPin("relay_1"), RPIGPIO.HIGH)
            RPIGPIO.output(self.config.getGpioPin("relay_2"), RPIGPIO.HIGH)

        state_real = str(self.getRelaysState()).lower()

        if str(state).lower() != state_real:
            logger(WARNING, self.CLASS,
                   "Failed to set heating to: {}. Returned state: {}".format(state, state_real))

        return state_real

    def temperature_to_relay_state(self, thermo_temperature: float, room_temperature: float):
        """
        Switch the heating on/off depending on the room temperature.
        TODO: To extend for multi rooms.

        Args:
            thermo_temperature: Temperature to which the thermostat is set to.
            room_temperature:   Temperature measured by the temperature sensor in the room.
        """
        if thermo_temperature <= round(room_temperature):
            logger(FINE, self.CLASS, "Setting 'Heating state OFF': set[{}] <= measured[{}]".format(
                thermo_temperature, round(room_temperature)))
            self.setRelaysState(HEATING_STATE_OFF)
        else:
            logger(FINE, self.CLASS, "Setting 'Heating state ON': set[{}] > measured[{}]".format(
                thermo_temperature, round(room_temperature)))
            self.setRelaysState(HEATING_STATE_ON)
