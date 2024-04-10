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
import json

import MySQLdb as SQL

from Common import logger, timestampToDatetime, validateDateTime
from Constants import CRITICAL, WARNING, FINE, FINER, FINEST
from Constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS


class DatabaseDAO:
    """
    Provides interface to MySQL database

    Created: 31.01.2018
    """

    def __init__(self):
        self.CLASS = "DatabaseDAO"
        self.db_conn = None

    def get_cursor(self):
        """
        Create or reuse database connection instance to provide the cursor

        Returns:
            Database connection cursor
        """
        if not self.db_conn:
            try:
                logger(FINER, self.CLASS,
                       "Connecting to database: host[{}], port[{}], name[{}], user[{}], pass[*****]."
                       .format(DB_HOST, DB_PORT, DB_NAME, DB_USER))
                self.db_conn = SQL.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, passwd=DB_PASS, db=DB_NAME, autocommit=True)
            except SQL.connector.Error as err:
                logger(CRITICAL, self.CLASS,
                       "Failed to connect to host[{}], port[{}], name[{}], user[{}], pass[****]:"
                       .format(DB_HOST, DB_PORT, DB_NAME, DB_USER))
                self.db_conn.close()
        else:
            logger(FINEST, self.CLASS, "Reusing connection..")

        logger(FINEST, self.CLASS, "Returning cursor..")
        self.db_conn.ping(True)
        return self.db_conn.cursor()

    def get_temperature_history(self, sensor: str = "sensor_1", period_start: str = None, period_end: str = None) -> json:
        """
        Function to retrieve the temperature for the Always ON thermostat setting.

        Args:
            sensor:         Name of the sensor that needs to be read. The actual ID will be retrieved from the configuration file.
            period_start:   Timestamp in the format "dd/mm/yyyy hh/mm"
            period_end:     Timestamp in the format "dd/mm/yyyy hh/mm"

        Returns:            The temperature readings for the past period as a JSON object
        Created:            31/03/2024
        """
        if not period_start or not validateDateTime(period_start):
            logger(FINER, self.CLASS, "Retrieving historical temperature failed to recognise start period: {}".format(period_start))
            period_start = "NOW() - INTERVAL 2 DAY"
        else:
            period_start = "\"{}\"".format(period_start)

        if not period_end or not validateDateTime(period_end):
            logger(FINER, self.CLASS, "Retrieving historical temperature failed to recognise end period: {}".format(period_end))
            period_end = "NOW()"
        else:
            period_end = "\"{}\"".format(period_end)

        """
        That doesnt work as the NOW() gets encapsulated in quotes and MySQL does not recognise it as a function.
        -----------------------------------------------
        query = "SELECT value, unit, datetime FROM temperature WHERE sensor = %s AND datetime >= %s AND datetime <= %s".format(
            sensor, period_start, period_end
        )
        logger(FINEST, self.CLASS, "SQL: {} -> sensor[{}], period_start[{}], period_end[{}].".format(
            query, sensor, period_start, period_end))
        """
        query = "SELECT value, unit, datetime FROM temperature WHERE sensor = \"{}\" AND datetime >= {} AND datetime <= {}".format(
            sensor, period_start, period_end
        )
        logger(FINEST, self.CLASS, "SQL: {}.".format(query))

        cursor = self.get_cursor()
        cursor.execute(query)
        logger(FINEST, self.CLASS, "SQL executed.")

        temperature_history_data = []
        for result in cursor:
            temperature_history_data.append({
                "datetime": "{}".format(result[2].timestamp()),
                "temperature": "{}".format(result[0]),
                "unit": "{}".format(result[1])
            })

        logger(FINER, self.CLASS, "Retrieved {} temperatures from the database.".format(len(temperature_history_data)))

        return json.dumps(temperature_history_data)

    def save_temperature(self, sensor: str, unit: str, temperature: float):
        """
        Function to save temperature reading from the sensor.

        Args:
            sensor:         Id of the sensor which read the temperature.
            unit:           Metrics of the measurement.
            temperature:    Value of the measurement.

        Returns:
            none
        """
        logger(FINE, self.CLASS, "Saving temperature measurement: sensor[{}], unit[{}], temperature[{}]."
               .format(sensor, unit, temperature))

        query = "INSERT INTO temperature (sensor, unit, value) VALUES (%s, %s, %s)"
        data = (sensor, unit, temperature)

        logger(FINEST, self.CLASS, "SQL: {} -> sensor[{}], unit[{}], temperature[{}]."
               .format(query, sensor, unit, temperature))

        self.get_cursor().execute(query, data)
        logger(FINEST, self.CLASS, "SQL executed.")

    def save_motion(self, sensor: str, motion_first: int, motion_last: int, activity_ranking: str):
        """
        Function to save detected motion from the PIR sensor on particular pin.

        Args:
            sensor:             Pin of the sensor which was motion activated.
            motion_first:       First motion detection.
            motion_last:        Last motion detection, assuming there were others in between.
            activity_ranking:   How many times the sensor was activated within this period of time.

        Returns:
            none

        TODO 1:   Create the database table

        TODO 2:   Here I assume that the database and the server are time and zone synchronised.
                  In an implementation where the database is on remote server, this method (as well as
                  all other components should be modified to use the database timestamp and not the server one.

        Created: 12.03.2018
        """
        motion_first_datetime = timestampToDatetime(motion_first)
        motion_last_datetime = timestampToDatetime(motion_last)

        logger(FINE, self.CLASS, "Saving detected motion: sensor[{}], motionFirst[{}], motionLast[{}]."
               .format(sensor, motion_first_datetime, motion_last_datetime))

        # Check if we have already started a record period with this start motion timestamp
        cursor = self.get_cursor()
        query = "SELECT * FROM presence WHERE sensor = %s AND motionFirst = %s"
        data = (sensor, motion_first_datetime)
        logger(FINEST, self.CLASS, "SQL: {} -> sensor[{}], motionFirst[{}]."
               .format(query, sensor, motion_first_datetime))
        cursor.execute(query, data)
        logger(FINEST, self.CLASS, "SQL executed.")

        if cursor.fetchone() is None:
            # We are starting a new motion period
            query = "INSERT INTO presence (sensor, motionFirst, motionLast, activityRanking) VALUES (%s, %s, %s, %s)"
            data = (sensor, motion_first_datetime, motion_last_datetime, activity_ranking)
            logger(FINEST, self.CLASS,
                   "SQL: {} -> sensor[{}], motionFirst[{}], motionLast[{}], activityRanking[{}]."
                   .format(query, sensor, motion_first_datetime, motion_last_datetime, activity_ranking))
        else:
            # We are updating an existing motion record period
            query = "UPDATE presence SET motionLast = %s, activityRanking = %s WHERE sensor = %s AND motionFirst = %s"
            data = (motion_last_datetime, activity_ranking, sensor, motion_first_datetime)
            logger(FINEST, self.CLASS,
                   "SQL: {} -> motionLast[{}], activityRanking[{}], sensor[{}], motionFirst[{}]."
                   .format(query, motion_last_datetime, activity_ranking, sensor, motion_first_datetime))

        cursor.execute(query, data)
        logger(FINEST, self.CLASS, "SQL executed.")

    def get_thermostat_manual(self) -> int:
        """
        Function to retrieve the temperature for the Always ON thermostat setting.

        Returns:    The temperature for Always ON thermostat setting.
        Created:    08/02/2024
        """
        query = "SELECT temperature FROM thermostat WHERE timeStart = \"00:00\" AND timeEnd = \"00:00\""
        logger(FINEST, self.CLASS, "SQL: {}.".format(query))
        cursor = self.get_cursor()
        cursor.execute(query)
        logger(FINEST, self.CLASS, "SQL executed.")

        thermo_temp = 0.0
        for value in cursor:
            thermo_temp = value[0]
            logger(FINER, self.CLASS, "Retrieved: 'thermostat Always ON temperature' -> {}".format(thermo_temp))

        return int(thermo_temp)

    def get_thermostat(self):
        """
        Function to retrieve the thermostat settings.

        Returns:    List of results of temperature time slots.
        Created:    10.12.2023
        """
        thermostat_settings = []
        query = "SELECT * FROM thermostat"

        logger(FINEST, self.CLASS, "SQL: {}.".format(query))
        cursor = self.get_cursor()
        cursor.execute(query)
        logger(FINEST, self.CLASS, "SQL executed.")

        for value in cursor:
            logger(FINER, self.CLASS, "Retrieved: {}".format(value))
            'Tuple(temperature-timeStart-timeEnd)'
            thermostat_settings.append(tuple([value[0], value[1], value[2]]))

        return thermostat_settings

    def set_thermostat_manual(self, temperature: int):
        """
        Function to set the thermostat temperature when in manual operation (no timer).
        The manual operation is when the start and end time are both set to `00:00`.

        Args:
            temperature:    Temperature to maintain
        Returns:
            none
        Created:
            06.02.2024
        """
        logger(FINE, self.CLASS, "Saving thermostat for manual operation to: {}.".format(temperature))
        self.set_thermostat(temperature, "00:00", "00:00")

    def set_thermostat(self, temperature: int, time_start: str, time_end: str):
        """
        Function to set the thermostat temperature.

        Args:
            temperature:    Temperature to maintain
            time_start:     Time in Hours:Minutes to start maintaining this temperature
            time_end:       Time in Hours:Minutes to stop maintaining this temperature,
                            falling back to the temperature setting for manual operation, or the next time slot.
        Return:
            none
        Created:
            01.02.2024
        """
        logger(FINE, self.CLASS, "Saving thermostat setting: temperature[{}], start[{}], end[{}]."
               .format(temperature, time_start, time_end))

        query = "UPDATE thermostat SET temperature=%s, timeStart=%s, timeEnd=%s"
        data = (temperature, time_start, time_end)

        logger(FINEST, self.CLASS, "SQL: {} -> temperature[{}], start[{}], end[{}]."
               .format(query, temperature, time_start, time_end))

        self.get_cursor().execute(query, data)
        logger(FINEST, self.CLASS, "SQL executed.")
        # self.db_conn.commit()

    def close(self):
        """
        Close database resources.
        Args:    none
        Returns: none
        Created: 02.02.2018
        """
        try:
            self.get_cursor().close()
            self.db_conn.close()
        except Exception as e:
            logger(WARNING, self.CLASS, "Failed to close database resources.")
        finally:
            logger(FINEST, self.CLASS, "Database resources closed.")
