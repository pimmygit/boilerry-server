#!/usr/bin/python

from datetime import timezone, datetime
from time import gmtime, strftime
from tokenize import String

from Constants import *
from ConfigStore import ConfigStore


def get_room_temperature(self) -> float:
    """
    Retrieves the room temperature reading from the sensor
    Returns:
        The room temperature reading
    Created:
        08/02/2024
    """
    thermo_units = self.config.setBoilerryServer(CONST_TEMPERATURE_UNITS, "C")
    room_temperature = self.thermo_sensor.getTemp(
        self.config.getSensor("sensor_1_id"),
        self.config.getSensor("sensor_1_timeout"),
        thermo_units
    )
    return float(room_temperature)


def getCurrentTime() -> str:
    return str(strftime("%Y-%m-%d %H:%M:%S", gmtime()))


def getCurrentTimeMinutes() -> int:
    return int(strftime("%M", gmtime()))


def hhmm_to_timestamp(hh_mm: String) -> float:
    """
    Converts time in the format HH:MM in today's timestamp

    Args:
        hh_mm:    String in the format HH:MM
    Returns:
        Today's datetime repressing the time specified by the HH_MM string
    """
    dt = datetime.strptime(hh_mm, "%H:%M")
    dt_now = datetime.now()
    dt = dt.replace(year=dt_now.year, month=dt_now.month, day=dt_now.day)
    return dt.timestamp()


def time_now_timestamp() -> float:
    return datetime.now().timestamp()


def timestampToDatetime(timestamp: int) -> str:
    """
    Converts UNIX timestamp to an SQL Datetime format

    Args:
        timestamp: UNIX timestamp in seconds
    Returns:
        Formatted datetime to store in database
    """
    utc_time = datetime.fromtimestamp(timestamp, timezone.utc)
    local_time = utc_time.astimezone()
    database_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
    logger(FINER, "Common", "UNIX timestamp[{}] converted to [{}].".format(timestamp, database_time))
    return database_time


def logger(level: int, caller: str, message: str):
    """
    Logs message to the screen or log file in a readable format

    Args:
        level:      The logging level in which the message should appear.
        caller:     The name of the class that prints the log information.
        message:    The Log message.
    Returns:
        none
    """
    config = ConfigStore()
    log_level = config.getLogLevel()
    log_out = config.getLogFile()

    if level <= log_level:
        if log_out == "stdout":
            print("{} {: >9} {: >15} {}".format(getCurrentTime(), LOG_LEVELS[level], caller, message))
        else:
            with open(log_out, "a") as file_runtime:
                file_runtime.write(
                    "{} {: >9} {: >15} {}\n".format(getCurrentTime(), LOG_LEVELS[level], caller, message))
