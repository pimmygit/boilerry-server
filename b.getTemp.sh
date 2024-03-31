#! /bin/sh

sudo python3 -c "from DS18B20 import *; temp_sens = DS18B20(); print(temp_sens.getTemp('28-0416a4e258ff', 'C', 30))"
