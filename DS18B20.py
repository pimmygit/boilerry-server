#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# (C) Copyright VAYAK Ltd (info@vayak.com). 2018, 2024
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

from Common import logger
from Constants import FINE, FINEST, FINER, WARNING


class DS18B20:
    """
    Provides interface to temperature sensor DS18B20
    Created: 31.01.2018
    """
    def __init__(self):
        self.CLASS = "DS18B20"

        # File containing the temperature sensor data. The sensor will periodically write data there,
        # we just need to read it.
        self.sensor_path = "/sys/bus/w1/devices/"
        self.sensor_output = "/w1_slave"

    def readFileLineByLine(self, file_path: str):
        """
        Function to read the content of the sensor data file.

        Args:
            file_path:  Full path to the file to be read.

        Returns:
            Content of the file line by line
        """
        logger(FINE, self.CLASS, "Reading file: {}".format(file_path))

        file_handle = open(file_path, 'r')
        file_lines = file_handle.readlines()

        file_handle.close()

        logger(FINEST, self.CLASS, "File content: {}".format(file_lines))

        return file_lines

    def getTemp(self, sensor_id: str, timeout: int, temp_units: str = 'C') -> float:
        """
        Function to parse the content of the file line by line and return the temperature:
            - First line gives status for successful read by the last three chars (YES).
            - Second line gives us the actual temperature value.

        Args:
            sensor_id:  Sensor to read
            timeout:    Timeout in seconds before giving up to read the temperature
            temp_units: [C]elsius or [F]ahrenheit. Default: [C]

        Returns:
            The measured temperature as a float value
        """
        logger(FINER, self.CLASS, "Reading sensor {} using [{}] metrics and timeout of {} seconds.".format(
            sensor_id, temp_units, timeout))

        timeout = timeout * 2
        curr_run = 0
        file_path = self.sensor_path + sensor_id + self.sensor_output
        file_lines = self.readFileLineByLine(file_path)

        # Keep re-reading the sensor output file until we have a good reading status
        while file_lines[0].strip()[-3:] != "YES":
            logger(FINER, self.CLASS, "On run {} we read status: {}".format(curr_run, file_lines[0].strip()[-3]))
            time.sleep(0.5)
            file_lines = self.readFileLineByLine(file_path)

            if curr_run > timeout:
                logger(WARNING, self.CLASS, "Sensor {} failed to read temperature within timeout of {} seconds.".format(
                    sensor_id, timeout))
                return -273

            curr_run += 1

        thermo_output = file_lines[1].find('t=')

        if thermo_output != -1:
            thermo_string = file_lines[1].strip()[thermo_output + 2:]
        else:
            thermo_string = 0.0

        if temp_units == "F":
            temperature = float(thermo_string) * 9.0 / 5.0 + 32.0
        else:
            temperature = float(thermo_string) / 1000.0

        logger(FINE, self.CLASS, "Sensor {} measured {} degrees.".format(sensor_id, temperature))

        return temperature
