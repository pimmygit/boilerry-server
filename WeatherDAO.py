#!/usr/bin/python
# import requests
from re import match
from typing import List, NamedTuple, Tuple

import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

from datetime import datetime

from Constants import *
from Common import logger, timestampToDatetime, timestampToDate, getCurrentDate


def retrieve_and_store_weather_history(self) -> None:
    """
    Retrieves the historical weather data

    Args:
        self:       The caller.
    Returns:
        str:        JSON String containing
    Created:
        19/10/2025
    """
    # We need to get when was the last weather record taken to retrieve the history starting from then.
    last_weather_record_timestamp = self.dao.get_weather_last_record_datetime()
    logger(FINER, "WeatherDAO", "Retrieved datetime of the last weather record: {}".format(
        datetime.fromtimestamp(last_weather_record_timestamp).strftime('%Y-%m-%d %H:%M:%S')))

    if last_weather_record_timestamp == 0.0:
        # If there is no record in the database yet, lets start with the minimum history specified in the Config file.
        min_days_history = self.config.getMetStation("min_days_history")
        if not min_days_history or min_days_history == "":
            last_weather_record_timestamp = datetime.now().timestamp() - 86400
        else:
            last_weather_record_timestamp = datetime.now().timestamp() - int(min_days_history) * 86400

    # We do not need to do anything if the last record was at least two hours ago or sooner.
    # The weather station would unlikely return anything for that period anyway.
    min_minutes_since_last_record = int(self.config.getMetStation("min_hours_since_last_record")) * 3600
    if last_weather_record_timestamp > datetime.now().timestamp() - min_minutes_since_last_record:
        logger(FINE, "WeatherDAO", "Skipping weather history polling because the last record is less than 2 hours ago: {}".format(
            timestampToDatetime(last_weather_record_timestamp)))
        return

    match self.config.getMetStation("api"):
        case "open-meteo":
            weather_history = api_open_meteo(
                self.config.getMetStation("latitude"),
                self.config.getMetStation("longitude"),
                self.config.getMetStation("unit_speed"),
                self.config.getMetStation("unit_temperature"),
                last_weather_record_timestamp)
        case "visual-crossing":
            weather_history = api_visual_crossing(self)
        case _:
            return

    logger(FINE, "WeatherDAO", "Retrieved {} hourly weather data points".format(len(weather_history)))

    # Enrich all existing indoor temperature measurements with the weather data
    self.dao.store_weather_history(weather_history)


def api_open_meteo(lat: str, lon: str, unit_speed: str, unit_temperature: str, last_weather_record_timestamp: int) \
        -> List[Tuple[str, str, float, float, float, str]]:
    """
    Retrieves the weather history for the specified period from OpenMeteo

    Args:
        lat:                            Observation station Latitude
        lon:                            Observation station Longitude
        unit_speed:                     Measurement unit of wind speed
        unit_temperature:               Measurement unit of temperature
        last_weather_record_timestamp:  Timestamp of the last weather record in the database.
    Returns:
        str:                            List of hourly weather measurements
    Created:
        19/10/2025
    """
    # API specific settings
    url = "https://archive-api.open-meteo.com/v1/archive"
    db_date_format = "%d/%m/%Y %H"

    try:
        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        # Make sure all required weather variables are listed here
        # The order of variables in hourly or daily is important to assign them correctly below
        params = {
            "latitude": lat,
            "longitude": lon,
            "unit_speed": unit_speed,
            "unit_temperature": unit_temperature,
            "start_date": timestampToDate(last_weather_record_timestamp),
            "end_date": getCurrentDate(),
            "hourly": ["temperature_2m", "apparent_temperature", "wind_speed_10m"]
        }
        logger(FINEST, "WeatherDAO", "Request string: {}".format(str(params)))

        responses = openmeteo.weather_api(url, params=params)
        logger(FINEST, "WeatherDAO", "Response received: OK")
    except Exception as e:
        logger(CRITICAL, "WeatherDAO", "Failed to fetch historical weather due to exception: {}".format(str(e)))
        return None

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    logger(FINEST, "WeatherDAO", "Coordinates: {}°N {}°E".format(response.Latitude(), response.Longitude()))
    logger(FINEST, "WeatherDAO", "Elevation: {} m asl".format(response.Elevation()))
    logger(FINEST, "WeatherDAO", "Timezone difference to GMT+0: {}s".format(response.UtcOffsetSeconds()))

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temp = hourly.Variables(0).ValuesAsNumpy()
    hourly_chill = hourly.Variables(1).ValuesAsNumpy()
    hourly_wind = hourly.Variables(2).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=False),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=False),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    ), "temperature_2m": hourly_temp,
        "apparent_temperature": hourly_chill,
        "wind_speed_10m": hourly_wind}

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    if hourly_dataframe.empty:
        logger(FINEST, "WeatherDAO", "No historical weather returned.")
        return None

    # We need to enrich the dataframe with extra data to match the database schema
    # Currently we have:
    #       date - temperature_2m - w_chill - wind
    # while we need:
    #       unit_speed - unit_temperature - temperature - w_chill - wind - date_format - date - date_format

    # 1. Add the extra data
    hourly_dataframe.insert(1, "unit_speed", unit_speed)
    hourly_dataframe.insert(2, "unit_temperature", unit_temperature)
    hourly_dataframe.insert(6, "db_date_format_1", db_date_format)
    hourly_dataframe.insert(7, "db_date_format_2", db_date_format)

    # 2. Reorder the columns to put the date which was at index 0 to the end.
    hourly_dataframe = hourly_dataframe.iloc[:, [1, 2, 3, 4, 5, 6, 0, 7]]

    # logger(FINEST, "WeatherDAO", "Hourly data: {}".format(hourly_dataframe))

    # Convert to list of (ordinary) tuples
    return list(hourly_dataframe.itertuples(index=False, name=None))


def api_visual_crossing(lat: str, lon: str, unit_speed: str, unit_temperature: str, last_weather_record_timestamp: int) \
        -> List[Tuple[str, str, float, float, float, str]]:
    """
    Retrieves the weather history for the specified period from VisualCrossing API

    TODO:   Note that this is incomplete API interface. It used to work, but since Visual Crossing made it paid,
            it no longer works and needs re-writing for commercial use.
    Args:
        lat:                            Observation station Latitude
        lon:                            Observation station Longitude
        unit_speed:                     Measurement unit of wind speed
        unit_temperature:               Measurement unit of temperature
        last_weather_record_timestamp:  Timestamp of the last weather record in the database.
    Returns:
        str:                            List of hourly weather measurements
    Created:
        19/10/2025
    """
    x_rapidapi_key = "c8d76b80bbmsh47bec07fecd79f3p18601bjsn85d5752a16da"
    x_rapidapi_host = "visual-crossing-weather.p.rapidapi.com"

    # for weather_info in weather_list_bulk:
    #     weather_datetime = weather_info["datetimeStr"]
    #     if not weather_datetime or weather_datetime == "":
    #         weather_datetime = datetime.now().timestamp()
    #     weather_temp = weather_info["temp"]
    #     if not weather_temp or weather_temp == "":
    #         weather_temp = 0.0
    #     weather_chill = weather_info["windchill"]
    #     if not weather_chill or weather_chill == "":
    #         weather_chill = 0.0
    #     weather_wind = weather_info["wspd"]
    #     if not weather_wind or weather_wind == "":
    #         weather_wind = 0.0
    #
    #     logger(FINER, "WeatherDAO", "Weather datetime received: {}".format(weather_datetime))
    #
    #     weather_history.append((
    #         weather_unit_speed,
    #         weather_unit_temp,
    #         float(weather_temp),
    #         float(weather_chill),
    #         float(weather_wind),
    #         '%d/%m/%Y %H',
    #         #datetime.strptime(weather_datetime, '%Y-%m-%dT%H:%M:%S%z'),
    #         parse(weather_datetime),
    #         '%d/%m/%Y %H'
    #     ))
    #
    # self.dao.store_weather_history(weather_history)


