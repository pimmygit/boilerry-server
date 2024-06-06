#!/usr/bin/python
import requests

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


def retrieve_weather_history(self) -> None:
    """
    Retrieves the room temperature reading from the sensor

    Args:
        self:           The caller.
    Returns:
        str:        JSON String containing
    Created:
        18/04/2024
    """
    # We need to get when was the last weather record taken to retrieve the history starting from then.
    response = None
    url = self.config.getMetStation("url")
    last_weather_record_timestamp = self.dao.get_weather_last_record_datetime()

    if last_weather_record_timestamp == 0.0:
        # If there is no record in the database yet, lets start with the minimum history specified in the Config file.
        min_days_history = self.config.getMetStation("min_days_history")
        if not min_days_history or min_days_history == "":
            last_weather_record_timestamp = datetime.now().timestamp() - 86400
        else:
            last_weather_record_timestamp = datetime.now().timestamp() - int(min_days_history) * 86400

    # We do not need to do anything if the last record was less than two hours ago.
    # The weather station would unlikely return anything for that period anyway.
    if last_weather_record_timestamp > datetime.now().timestamp() - 7200:
        logger(FINE, "Common", "Skipping weather history polling. Last record is less than 2 hours ago: {}".format(
            timestampToDatetime(last_weather_record_timestamp)))
        return

    http_headers = {
        "content-type": "application/json",
        "X-RapidAPI-Host": self.config.getMetStation("x_rapidapi_host"),
        "X-RapidAPI-Key": self.config.getMetStation("x_rapidapi_key")
    }

    http_request = {
        "startDateTime": timestampToDatetime(last_weather_record_timestamp),
        "endDateTime": getCurrentTime(),
        "aggregateHours": "1",
        "location": self.config.getMetStation("location"),
        "contentType": "json",
        "unitGroup": self.config.getMetStation("unitGroup"),
        "shortColumnNames": "0"
    }

    try:
        response = requests.get(url, headers=http_headers, params=http_request)
    except requests.exceptions.Timeout:
        logger(WARNING, "Common", "Timeout connecting to: {}".format(url))
    except requests.exceptions.TooManyRedirects:
        logger(WARNING, "Common", "Wrong URL used (too many redirects): {}".format(url))
    except requests.exceptions.RequestException as e:
        logger(WARNING, "Common", "Request failed for: {}".format(url))
        return

    weather_dict = response.json()
    weather_unit_temp = weather_dict["columns"]["temp"]["unit"][3]
    weather_unit_speed = weather_dict["columns"]["wspd"]["unit"]
    weather_list_bulk = weather_dict["locations"][self.config.getMetStation("location")]["values"]

    # Verify that the weather station has returned any results
    if not weather_list_bulk:
        logger(FINE, "Common", "The weather station did not return any results for the period since: {}".format(
            timestampToDatetime(last_weather_record_timestamp)))
        return

    weather_history = []
    for weather_info in weather_list_bulk:
        weather_datetime = weather_info["datetimeStr"]
        if not weather_datetime or weather_datetime == "":
            weather_datetime = datetime.now().timestamp()
        weather_temp = weather_info["temp"]
        if not weather_temp or weather_temp == "":
            weather_temp = 0.0
        weather_chill = weather_info["windchill"]
        if not weather_chill or weather_chill == "":
            weather_chill = 0.0
        weather_wind = weather_info["wspd"]
        if not weather_wind or weather_wind == "":
            weather_wind = 0.0

        weather_history.append((
            weather_unit_speed,
            weather_unit_temp,
            float(weather_temp),
            float(weather_chill),
            float(weather_wind),
            '%d/%m/%Y %H',
            datetime.strptime(''.join(weather_datetime.rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z'),
            '%d/%m/%Y %H'
        ))

    self.dao.store_weather_history(weather_history)


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
    database_time = local_time.strftime("%Y-%m-%dT%H:%M:%S")
    # logger(FINER, "Common", "UNIX timestamp[{}] converted to [{}].".format(timestamp, database_time))
    return database_time


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
