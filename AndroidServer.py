#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# v.1.0.0 | 24.02.2018
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
import json
from json import JSONDecodeError

import websockets

from Common import logger
from ConfigStore import ConfigStore
from Constants import CONST_GET_STATE
from Constants import CONST_THERMO_STATE, CONST_THERMO_TEMPERATURE, CONST_TEMPERATURE_ROOM, CONST_THERMO_SWITCH
from Constants import WARNING, INFO, FINE, FINER, FINEST
from DS18B20 import DS18B20
from DatabaseDAO import DatabaseDAO
from GPIO import GPIO
from Thermostat import Thermostat


def init_response():
    """
    Name:     initResponse
    Desc:     Build the response JSON structure
              {
                  "CONST_THERMO_STATE": "True",
                  "CONST_THERMO_SWITCH": "1",
                  "CONST_THERMO_TEMPERATURE": "0.0",
                  "CONST_TEMPERATURE_ROOM": "0.0"
              }
    Param:    none
    Return:   none
    Modified: 07/12/2023
    """
    json_response = "{"
    json_response += "\"" + CONST_THERMO_STATE + "\": \"True\", "
    json_response += "\"" + CONST_THERMO_SWITCH + "\": \"1\", "
    json_response += "\"" + CONST_THERMO_TEMPERATURE + "\": \"0.0\", "
    json_response += "\"" + CONST_TEMPERATURE_ROOM + "\": \"0.0\""
    json_response += "}"

    return json.loads(json_response)


class AndroidServer:
    """
    Provides mechanism to allow Android app to connect and modify the
    heating system configuration.
    We intentionally allow only one single connection to ensure only
    a singe person modifies the heating configuration.
    -----------------------------------------------------------------
    1.0.0. | 24.02.2018 - First version
    """
    def __init__(self, dao: DatabaseDAO, gpio: GPIO, sensor: DS18B20):
        """
        Initialise and start the thread which listens for connections and act on requests.

        Args:
            dao:    Database Access Object: MySQL database
            gpio:   The interface to external peripheral
            sensor: USB temperature sensor
        Return:
            none
        Created:
            24.02.2018
        """
        self.CLASS = "AndroidServer"
        self.config = ConfigStore()
        self.dao = dao
        self.gpio = gpio
        self.thermo_sensor = sensor

        def_host = ""
        def_port = "9741"

        logger(FINER, self.CLASS, "Opening WebSocket on port: {}..".format(self.config.getAndroidServer("port", def_port)))
        handler = websockets.serve(self.process_request, self.config.getAndroidServer("host", def_host), self.config.getAndroidServer("port", def_port))
        logger(FINER, self.CLASS, "Handler created.".format(self.config.getAndroidServer("port", def_port)))
        asyncio.get_event_loop().run_until_complete(handler)
        logger(FINER, self.CLASS, "Websocket created.".format(self.config.getAndroidServer("port", def_port)))
        """Nothing below the line above will get executed - it loops the asyncio forever."""
        asyncio.get_event_loop().run_forever()

    def get_json_from_request(self, request_string: str):
        """
        Parses the request to retrieve the action, parameter and value
        WARNING: Virtually no security here. The accepted format of the request is:
            pimmy<get|set>tayna<param_name>parola[value]
        Note: We expect the length of the parameter name to be at least three characters long.

        Args:
            request_string: Request string from the client
        Returns:
            Tuple(action[0], parameter[1], value[2])
        Modified: 08.04.2018
        """
        logger(FINER, self.CLASS, "Loading request string: {}".format(request_string))

        try:
            json_request = json.loads(request_string)
        except JSONDecodeError as e:
            logger(WARNING, self.CLASS, "Invalid JSON received - ignoring request.")
            return None

        if len(json_request) < 1:
            logger(INFO, self.CLASS, "Zero length JSON received - ignoring request.")
            return None
        else:
            return json_request

    def validate_request(self, json_request: json) -> json:
        """
        Checks that all expected elements in the JSON request are present

        Args:
            json_request:   JSON Request object from the client
        Returns:
            True if validates successfully, False otherwise
        Created:
            11/Dec/2023
        """
        try:
            if json_request["name"] == CONST_GET_STATE:
                # We are not changing the state of the boiler, just getting its state.
                return True
        except KeyError:
            logger(WARNING, self.CLASS, "JSON has no element: name")
            return False

        try:
            if json_request["value"] is None:
                logger(WARNING, self.CLASS, "JSON element value is None.")
        except KeyError:
            logger(WARNING, self.CLASS, "JSON has no element: value")
            return False

        return True

    def build_state_response(self, thermostat):
        """
        Name:       build_state_response()
        Desc:       Checks that all expected elents in the JSON request are present

        Param:      thermostat  -> Object containing all thermostat's values at this moment
        Return:     -> JSON: Status of the boiler
        Modified:   11/Dec/2023
        """
        json_module_response = init_response()

        # Get the thermostat state
        json_module_response[CONST_THERMO_STATE] = thermostat.get_thermo_state()
        logger(FINEST, self.CLASS, "State->{}: {}".format(
            CONST_THERMO_STATE, str(json_module_response[CONST_THERMO_STATE]).lower()))

        # Get the thermostat switch position
        json_module_response[CONST_THERMO_SWITCH] = thermostat.get_thermo_switch()
        logger(FINEST, self.CLASS, "State->{}: {}".format(
            CONST_THERMO_SWITCH, json_module_response[CONST_THERMO_SWITCH]))

        # Get the thermostat temperature value for the Always ON setting (timeStart="00:00" and timeEnd="00:00":
        json_module_response[CONST_THERMO_TEMPERATURE] = thermostat.get_thermo_manual_temperature()
        logger(FINEST, self.CLASS, "DAO result: thermostat->manual_temp[{}]".format(thermostat.get_thermo_manual_temperature()))

        # Get the current room temperature
        json_module_response[CONST_TEMPERATURE_ROOM] = thermostat.get_room_temperature()
        logger(FINEST, self.CLASS, "State->{}: {}".
               format(CONST_TEMPERATURE_ROOM, json_module_response[CONST_TEMPERATURE_ROOM]))

        logger(FINER, self.CLASS, "Sending response: {}".format(json.dumps(json_module_response)))
        return json_module_response

    async def process_request(self, websocket: websockets, path):
        """
        Determines and fires the action based on the request

        Args:
            websocket:  Request string received by the websocket.
            path:       Absolutely no idea why this cannot be optional.
        Return:
            none
        Created:
            25.02.2018
        """
        async for request_string in websocket:
            json_request = self.get_json_from_request(request_string)

            if json_request is None or not self.validate_request(json_request):
                return None

            logger(FINE, self.CLASS, "Processing request: {}".format(json.dumps(json_request)))

            if json_request["name"] == CONST_THERMO_SWITCH:
                self.config.setBoilerryServer(CONST_THERMO_SWITCH, str(json_request["value"]))
                """
                if int(json_request["value"]) > 0:
                    if not self.thermostat.is_alive():
                        self.thermostat.start()
                else:
                    self.thermostat.stop()
                """
            # At some point, we would be able to set temperature for time slots
            # Time slot 00:00-00:00 is the temperature for the "Always On" state of the master switch.
            if json_request["name"] == CONST_THERMO_TEMPERATURE:
                self.dao.set_thermostat(json_request["value"], "00:00", "00:00")

            # Create the thermostat object with the latest from the DB and sensors
            thermostat = Thermostat(self.dao, self.gpio, self.thermo_sensor)

            # Process the newly received settings immediately
            self.gpio.temperature_to_relay_state(thermostat.get_thermo_manual_temperature(), thermostat.get_room_temperature())
            # After changing the relay state, we must update the Thermostat object
            thermostat.refresh_thermo_state()

            # Regardless of the request/command that was sent to the server (us),
            # we respond with the full state of the system
            await websocket.send(json.dumps(self.build_state_response(thermostat)))
            logger(FINEST, self.CLASS, "Response sent.")