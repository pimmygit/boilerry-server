#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# (C) Copyright VAYAK Ltd (info@vayak.com). 2024
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
import configparser
import time
import os
import pathlib

from Constants import CONFIG_UPDATE_PERIOD, LOG_LEVELS


class Singleton(type):
    """
    As this is called from various places, we are implementing this class as a Singleton through metaclasses.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConfigStore(metaclass=Singleton):
    """
    On-demand pull of the settings from the file config store,
    allowing the user to update them without the need to restart the application.

    Created: 20/03/1024
    """

    def __init__(self, home_dir: str = "/opt/boilerry", config_file: str = "boilerry.ini"):
        """
        Instance creation method for the Database and File configuration stores.

        Args:
            home_dir (str):  Absolute path to the application's home directory.
            config_file (str):  Name of the configuration file to use.

        Returns:
            none

        Modified: [20/03/2024]
        """
        super().__init__()
        self.CLASS = "ConfigStore"

        self.file = os.environ.get("BOILERRY_HOME", home_dir) + "/" + config_file
        if "BOILERRY_HOME" in os.environ:
            home_dir = os.environ.get("BOILERRY_HOME")

        if not os.path.isdir(home_dir):
            print("Invalid application's home directory: {}".format(home_dir))
            print("Check your environment variable: BOILERRY_HOME")
            exit(1)

        self.file = os.path.join(os.getcwd(), home_dir, config_file)
        if not os.path.exists(self.file):
            print("Config file not found: {}".format(self.file))
            exit(1)

        self.config = configparser.ConfigParser()
        self.config_read_time = 0

    def readConfig(self):
        """
        Read the config no nore often than every minute
        """
        if self.config_read_time + CONFIG_UPDATE_PERIOD <= int(time.time()):
            self.config_read_time = int(time.time())
            try:
                """ TODO: provide a path to the ini file"""
                with open(self.file) as file:
                    self.config.read_file(file)
            except IOError:
                print("Failed to read configuration file '{}'. Using defaults.".format(self.file))

    def getLogLevel(self) -> int:
        """
        Retrieves the log level from the INI config file as an integer.

        Return:
            int: The value of the logging property stored in the INI config file, or its default value.

        Modified: [21.03.2024]
        """
        self.readConfig()
        return LOG_LEVELS.index(self.config['logging'].get("level", "INFO"))

    def getLogFile(self) -> str:
        """
        Returns the logging output as specified in the INI config file.

        Return:
            str: The file name or STDOUT, or its default value as stored in the INI config file.

        Modified: [21.03.2024]
        """
        self.readConfig()
        return self.config['logging'].get("file", "stdout")

    def getMetStation(self, property_name: str) -> str:
        """
        Retrieves meteorological station API settings from the INI config file.

        Args:
            property_name: The name of the property defined in the INI config file.

        Return:
            str: The property value stored in the INI config file. There are no default values.

        Created: [18.04.2024]
        """
        self.readConfig()
        property_value = self.config['weather'].get(property_name.lower())

        if property_value and property_value != "":
            return property_value

        return ""

    def getSensor(self, property_name: str) -> str:
        """
        Retrieves temperature sensor properties from the INI config file. The temperature sensor properties are
        strictly defined, and without them the application cannot operate.

        Args:
            property_name: The name of the property defined in the INI config file.

        Return:
            str: The property value stored in the INI config file. There are no default values.

        Modified: [23.03.2024]
        """
        self.readConfig()
        property_value = self.config['temperature.sensor'].get(property_name.lower())

        if property_value and property_value != "":
            return property_value

        """
        If we have failed to return the sensor property, it means we cannot measure temperature,
        hence the application is non-operable.
        """
        """logger(CRITICAL, self.CLASS, "Failed to read property '{}' from file: {}.".format(property_name, self.file))"""
        exit(1)

    def getGpioPin(self, property_name: str) -> int:
        """
        Retrieves the GPIO PIN for the given property as specified in the INI config file. The GPIO properties are
        strictly defined, and without them the application cannot operate, hence there are no default values.

        Args:
            property_name: The name of the property defined in the INI config file.

        Return:
            str: The property value stored in the INI config file. There are no default values.

        Modified: [23.03.2024]
        """
        self.readConfig()
        property_value = self.config['pin.gpio'].get(property_name)

        if property_value and property_value != "":
            return int(property_value)

        """
        If we have failed to return the GPIO PIN, it means we cannot connect to interface,
        hence the application is non-operable.
        """
        """logger(CRITICAL, self.CLASS, "Failed to read property '{}' from file: {}.".format(property_name, self.file))"""
        exit(1)

    def getAndroidServer(self, property_name: str, property_default: str) -> str:
        """
        Retrieves the android server settings from the INI config file.

        Args:
            property_name:      The name of the property defined in the INI config file.
            property_default:   The default value in case the property does not exist in the INI config file.

        Return:
            str: The value of the property stored in the INI config file, or its default value.

        Modified: [23.03.2024]
        """
        self.readConfig()
        return self.config['android.server'].get(property_name, property_default)

    def getBoilerryServer(self, property_name: str, property_default: str) -> str:
        """
        Retrieves the heating system server settings from the INI config file.
        These are all the configurations the user can change via the UI.

        Args:
            property_name:      The name of the property defined in the INI config file.
            property_default:   The default value in case the property does not exist in the INI config file.

        Return:
            str: The value of the property stored in the INI config file, or its default value.

        Modified: [25.03.2024]
        """
        self.readConfig()
        return self.config['boilerry.server'].get(property_name.lower(), property_default)

    def setBoilerryServer(self, property_name: str, property_value: str):
        """
        Retrieves the heating system server settings from the INI config file.
        These are all the configurations the user can change via the UI.

        Args:
            property_name:    The name of the property to update in the INI config file.
            property_value:   The value of the property to be set in the INI config file.
        Return:
            none
        Modified: [25.03.2024]
        """
        self.config['boilerry.server'][property_name.lower()] = property_value
        with open(self.file, 'w') as config_file:
            self.config.write(config_file)
