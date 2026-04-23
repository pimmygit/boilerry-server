#!/usr/bin/python
# import requests
from typing import List, Tuple

import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

from datetime import datetime

from ConfigStore import ConfigStore
from DatabaseDAO import DatabaseDAO
from Constants import *
from Common import logger, timestampToDatetime, timestampToDate, getCurrentDate, getCurrentTime


class WeatherDAO:
    def __init__(self, config: ConfigStore, dao_db: DatabaseDAO):
        """
        Create object and initialize

        Args:
            self:               The caller.
            config:             Config Store
            dao_db:             DatabaseDAO
        Returns:
            str:                JSON String containing
        Created:
            17/04/2026
        """
        self.config = config
        self.dao_db = dao_db

        self.latitude = config.getMetStation("latitude")
        self.longitude = config.getMetStation("longitude")
        self.unit_speed = config.getMetStation("unit_speed")
        self.unit_temperature = config.getMetStation("unit_temperature")
        self.min_days_history = config.getMetStation("min_days_history")

    def retrieve_and_store_weather_history_periodically(self) -> None:
        """
        Just a wrapper that states it is called by a scheduler

        Args:
            self:               The caller,
        Returns:
            str:                None
        Created:
            20/04/2026
        """
        logger(FINE, "WeatherDAO", "Periodic retrieval of the weather history at '{}'."
               .format(self.config.getMetStation("time_to_retrieve_weather_history")))
        self.retrieve_and_store_weather_history()

    def retrieve_and_store_weather_history(self) -> None:
        """
        Retrieves the historical weather data and stores it in the database

        Args:
            self:               The caller,
        Returns:
            str:                None
        Created:
            19/10/2025
        """
        # Check the timestamp of the last weather record so that we can retrieve the history starting from then.
        last_weather_record_timestamp = int(
            self.dao_db.get_last_weather_record_timestamp(int(self.config.getMetStation("min_days_history"))))

        # We want to avoid hitting the API too often, hence we impose a minimum time period before we can send a request again.
        min_hours_since_last_record = int(self.config.getMetStation("min_hours_since_last_record"))
        if last_weather_record_timestamp > datetime.now().timestamp() - min_hours_since_last_record * 3600:
            logger(FINE, "WeatherDAO",
                   "Skipping weather history polling because the last record is less than {} hours ago: {}".format(
                       min_hours_since_last_record, timestampToDatetime(last_weather_record_timestamp)))
            return

        match self.config.getMetStation("api"):
            case "open-meteo":
                weather_history = self.api_open_meteo(last_weather_record_timestamp)
            case "visual-crossing":
                weather_history = self.api_visual_crossing()
            case _:
                return

        logger(FINE, "WeatherDAO", "Retrieved {} hourly weather data points".format(len(weather_history)))

        # Enrich all existing indoor temperature measurements with the weather data
        # The Weather API will return the full 24 hours of data for that day, while we only need to update the missing hours,
        # hence we pass the 'last_weather_record_timestamp' too.
        self.dao_db.store_weather_history(last_weather_record_timestamp, weather_history)

    def api_open_meteo(self, last_weather_record_timestamp: int) -> List[Tuple[str, str, float, float, float, str, str, str]]:
        """
        Retrieves the weather history for the specified period from OpenMeteo

        Args:
            last_weather_record_timestamp:  The timestamp in seconds of the last weather record.
        Returns:
            str:                            List of hourly weather measurements.
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
                "latitude": self.latitude,
                "longitude": self.longitude,
                "unit_speed": self.unit_speed,
                "unit_temperature": self.unit_temperature,
                "start_date": timestampToDate(last_weather_record_timestamp),
                "end_date": getCurrentDate(),
                "hourly": ["temperature_2m", "apparent_temperature", "wind_speed_10m"]
            }
            logger(FINEST, "WeatherDAO", "Request string: {}".format(str(params)))

            responses = openmeteo.weather_api(url, params=params)
            # logger(FINEST, "WeatherDAO", "Response received: OK")
        except Exception as e:
            logger(CRITICAL, "WeatherDAO", "Failed to fetch historical weather due to exception: {}".format(str(e)))
            return None

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]
        # logger(FINEST, "WeatherDAO", "Coordinates: {}°N {}°E".format(response.Latitude(), response.Longitude()))
        # logger(FINEST, "WeatherDAO", "Elevation: {} meters Above Sea Level (ASL).".format(response.Elevation()))
        # logger(FINEST, "WeatherDAO", "Timezone difference to GMT+0: {}s".format(response.UtcOffsetSeconds()))

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

        # logger(FINEST, "WeatherDAO", "API Dataframe: {}".format(hourly_dataframe))

        # A.) For maximum performance, we discard all elements for time earlier than the time now,
        # and older than 'last_weather_record_timestamp', because
        # these times are either yet not available in the database, or already updated.
        # If we dont remove them, we would be updating the database unnecessary, loosing 0.5 sec per update.
        # 1. Ensure the first column is datetime (assuming it's the first column at index 0)
        first_col = hourly_dataframe.columns[0]
        hourly_dataframe[first_col] = pd.to_datetime(hourly_dataframe[first_col])

        # 2. Filter the rows specifically on that column
        mask = (hourly_dataframe[first_col] >= timestampToDatetime(last_weather_record_timestamp)) & \
               (hourly_dataframe[first_col] <= getCurrentTime())
        df_filtered = hourly_dataframe[mask]

        # B.) We need to enrich the dataframe with extra data to match the database schema
        # Currently we have:
        #       date - temperature_2m - w_chill - wind
        # while we need:
        #       unit_speed - unit_temperature - temperature - w_chill - wind - date_format - date - date_format
        # 1. Add the extra data
        df_filtered.insert(1, "unit_speed", self.unit_speed)
        df_filtered.insert(2, "unit_temperature", self.unit_temperature)
        df_filtered.insert(6, "db_date_format_1", db_date_format)
        df_filtered.insert(7, "db_date_format_2", db_date_format)

        # 2. Reorder the columns to put the date which was at index 0 to the end.
        df_filtered = df_filtered.iloc[:, [1, 2, 3, 4, 5, 6, 0, 7]]

        # logger(FINEST, "WeatherDAO", "Filtered and enriched DF: {}".format(df_filtered))

        # Convert to list of (ordinary) tuples
        return list(df_filtered.itertuples(index=False, name=None))

    def api_visual_crossing(self) -> List[Tuple[str, str, float, float, float, str, str, str]]:
        """
        Retrieves the weather history for the specified period from VisualCrossing API

        TODO:   Note that this is incomplete API interface. It used to work, but since Visual Crossing made it paid,
                it no longer works and needs re-writing for commercial use.
        Args:
        Returns:
            List:                            List of hourly weather measurements
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
