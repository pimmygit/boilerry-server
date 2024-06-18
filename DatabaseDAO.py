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
from typing import List, Tuple

import MySQLdb as SQL

from Common import logger, timestampToDatetime, validateDateTime, mpt
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
                self.db_conn = SQL.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, passwd=DB_PASS, db=DB_NAME,
                                           autocommit=True)
            except SQL.connector.Error as err:
                logger(CRITICAL, self.CLASS,
                       "Failed to connect to host[{}], port[{}], name[{}], user[{}], pass[****]:"
                       .format(DB_HOST, DB_PORT, DB_NAME, DB_USER))
                self.db_conn.close()
        # else:
        #    logger(FINEST, self.CLASS, "Reusing connection..")

        # logger(FINEST, self.CLASS, "Returning cursor..")
        self.db_conn.ping(True)
        return self.db_conn.cursor()

    def get_weather_last_record_datetime(self) -> float:
        """
        Function to retrieve the date time of when the last weather record was taken.

        Args:
        Returns:            The datetime of when the last weather record was taken.
        Created:            18/04/2024
        """
        query = "SELECT datetime FROM temperature WHERE temperature IS NULL ORDER BY datetime ASC LIMIT 1"

        logger(FINEST, self.CLASS, "SQL: {}.".format(query))

        cursor = self.get_cursor()
        cursor.execute(query)
        logger(FINEST, self.CLASS, "SQL executed.")

        for result in cursor:
            logger(FINER, self.CLASS, "Retrieved datetime of the last weather record: {}".format(
                timestampToDatetime(int(result[0].timestamp()))))
            return result[0].timestamp()

        return 0.0

    def store_weather_history(self, weather_history: List[Tuple[str, str, float, float, float, str]]) -> None:
        """
        Function to populate all property temperature readings with historical weather data.

        The weather history comes at an hourly period, while the property temperature is recorded more often.
        Therefore, we would end up with duplicate weather records for a bunch of property temperature readings
        that fall within the same hour... hence the 'strange' date comparison in the SQL statement here.

        Args:
            weather_history:    List of Tuples containing weather measurements.
        Returns:
            None
        Created:
            18/04/2024
        """
        logger(FINE, self.CLASS, "Saving {} weather history measurements.".format(len(weather_history)))

        query = """UPDATE temperature 
        SET unit_speed = %s, unit_temperature = %s, temperature = %s, windchill = %s, wspd = %s 
        WHERE DATE_FORMAT(datetime, %s) = DATE_FORMAT(%s, %s)"""

        for measurement in weather_history:
            self.get_cursor().execute(query, measurement)

        logger(FINEST, self.CLASS, "SQL executed.")

    def get_temperature_history(self, period_start: str = None, period_end: str = None) -> str:
        """
        Function to retrieve the temperature for the Always ON thermostat setting.

        Args:
            period_start:   Timestamp in the format "dd/mm/yyyy hh/mm"
            period_end:     Timestamp in the format "dd/mm/yyyy hh/mm"

        Returns:            The temperature readings for the past period as a JSON string
        Created:            31/03/2024
        """
        if not period_start or not validateDateTime(period_start):
            logger(FINER, self.CLASS,
                   "Retrieving historical temperature failed to recognise start period: {}".format(period_start))
            period_start = "NOW() - INTERVAL 2 DAY"
        else:
            period_start = "\"{}\"".format(period_start)

        if not period_end or not validateDateTime(period_end):
            logger(FINER, self.CLASS,
                   "Retrieving historical temperature failed to recognise end period: {}".format(period_end))
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
        query = "SELECT * FROM temperature WHERE datetime >= {} AND datetime <= {}".format(period_start, period_end)
        logger(FINEST, self.CLASS, "SQL: {}.".format(query))

        cursor = self.get_cursor()
        cursor.execute(query)
        logger(FINEST, self.CLASS, "SQL executed.")

        temperature_history_data = []
        for rs in cursor:
            temperature_data_string = "{" + """ "datetime": "{}", "time_state_on": "{}", "unit_speed": "{}", "unit_temperature": "{}", "temperature": "{}", "windchill": "{}", "wspd": "{}", "sensor_1": "{}", "sensor_2": "{}", "sensor_3": "{}" """.format(
                                           rs[0], rs[1], rs[2], rs[3], rs[4], rs[5], rs[6], rs[7], rs[8], rs[9]) + "}"
            temperature_history_data.append(temperature_data_string)

        logger(FINER, self.CLASS, "Retrieved {} temperatures from the database.".format(len(temperature_history_data)))

        temperature_history_data = json.dumps(temperature_history_data)
        temperature_history_data = temperature_history_data.replace("\"{", "{")
        temperature_history_data = temperature_history_data.replace("\\", "")
        temperature_history_data = temperature_history_data.replace("\"\"", "\"")
        temperature_history_data = temperature_history_data.replace("}\"", "}")
        temperature_history_data = temperature_history_data.replace("None", "")

        #response_log = (json.dumps(temperature_history_data)[:300] + '..(truncated)') if len(json.dumps(temperature_history_data)) > 300 else json.dumps(temperature_history_data)
        #logger(FINEST, self.CLASS, "Json: {}".format(response_log))

        return temperature_history_data

    def save_temperature(self, seconds_heating_on: int, unit: str,
                         sensor_1: float = None, sensor_2: float = None, sensor_3: float = None):
        """
        Function to save temperature reading from the sensor.

        Args:
            seconds_heating_on: Time in seconds for which the boiler was heating during the past reading period.
            unit:               Metrics of the measurement.
            sensor_1:           Measured temperature by sensor_1.
            sensor_2:           Measured temperature by sensor_2.
            sensor_3:           Measured temperature by sensor_3.

        Returns:
            none
        """
        logger(FINE, self.CLASS, "Saving temperature measurement: time_state_on[{}], unit[{}], s1[{}], s2[{}], s3[{}]."
               .format(seconds_heating_on, unit, sensor_1, sensor_2, sensor_3))

        query = "INSERT INTO temperature (time_state_on, unit_speed, unit_temperature, sensor_1, sensor_2, sensor_3) VALUES (%s, %s, %s, %s, %s, %s)"
        data = (seconds_heating_on, 'mph', unit, sensor_1, sensor_2, sensor_3)

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
