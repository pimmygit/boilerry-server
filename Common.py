#!/usr/bin/python
from datetime import timezone, datetime
from dateutil.parser import parse
from time import gmtime, strftime, sleep

from Constants import *
from ConfigStore import ConfigStore


def read_temperature_now(self, sensor: str = "sensor_1") -> float:
    """
    Retrieves the room temperature reading from the sensor

    Args:
        self:       The caller.
        sensor:     Which sensor to read, as defined in the boilerry.ini file
    Returns:
        float:      The room temperature reading
    Created:
        08/02/2024
    """
    thermo_units = self.config.setBoilerryServer(CONST_TEMP_UNITS, "C")
    room_temperature = self.thermo_sensor.getTemp(
        self.config.getSensor(sensor + "_id"),
        self.config.getSensor(sensor + "_timeout"),
        thermo_units
    )
    return float(room_temperature)


def validateDateTime(datetime_text: str) -> bool:
    """
    Verifies that the date is in the right format.

    Args:
        datetime_text:  Datetime to validate for accurate format: %Y-%m-%d %H:%M:%S

    Returns:
        bool:           True if validated OK, false otherwise.
    """
    try:
        return bool(parse(datetime_text, dayfirst=True))
    except ValueError:
        return False


def getCurrentTime() -> str:
    return str(strftime("%Y-%m-%dT%H:%M:%S", gmtime()))


def getCurrentDate() -> str:
    return str(strftime("%Y-%m-%d", gmtime()))


def getCurrentTimeMinutes() -> int:
    return int(strftime("%M", gmtime()))


def hhmm_to_timestamp(hh_mm: str) -> float:
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


def timestampToLocaLTime(timestamp: int) -> datetime:
    """
    Converts UNIX timestamp to an datetime object

    Args:
        timestamp: UNIX timestamp in seconds
    Returns:
        Localized datetime
    """
    utc_time = datetime.fromtimestamp(timestamp, timezone.utc)
    local_time = utc_time.astimezone()
    return local_time


def timestampToDatetime(timestamp: int) -> str:
    """
    Converts UNIX timestamp to an SQL Datetime format

    Args:
        timestamp: UNIX timestamp in seconds
    Returns:
        Formatted datetime to store in database
    """
    return timestampToLocaLTime(timestamp).strftime("%Y-%m-%dT%H:%M:%S")


def timestampToDate(timestamp: int) -> str:
    """
    Converts UNIX timestamp to an SQL Datetime format

    Args:
        timestamp: UNIX timestamp in seconds
    Returns:
        Formatted datetime to store in database
    """
    return timestampToLocaLTime(timestamp).strftime("%Y-%m-%d")


def sleep_to_next_minute(sleep_interval: int) -> None:
    """
    Ensures the sleeping ends at the first second of the new minute. For example, if we start sleeping for a minute
    at 18:47:55, we will end sleeping at 18:48:00. Yes we slept less than 60 seconds, but we woke up at the beginning
    of the next minute.
    This is to ensure that the MOD calculation for when to take recording is not mislead. I.e. We run the loop every
    minute, while the processing may take up to a second. If we start processing at 14:00:00, by the time Close to the end of the hour, we could easily check if
    we need to record the temperature 1 second later, not detecting that it was that minute when it should have happened.

    Args:
        sleep_interval:     Time in seconds to sleep
    """
    sleep_start_minute = getCurrentTimeMinutes()

    while (sleep_start_minute + sleep_interval - 1) == getCurrentTimeMinutes():
        sleep(1)


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
