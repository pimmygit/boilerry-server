#!/usr/bin/python
###################################################################
# Heating system control with Raspberry Pi
# -----------------------------------------------------------------
# v.1.0.0 | 04.02.2018
#
# (C) Copyright VAYAK Ltd (info@vayak.com). 2018  
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
import datetime
import threading
import RPi.GPIO as GPIO

from Constants import *
from Common import *

from DatabaseDAO import DatabaseDAO


class MotionRecorder(threading.Thread):
    """
    Provides mechanism to monitor and record motions detected by the PIR sensor.
    -----------------------------------------------------------------
    1.0.0. | 04.02.2018 - First version
    """
    def __init__(self, gpio_pin_pir):
        """
        Name:     __init__(Integer, Integer)
        Desc:     Initialise and start the thread which listens and stored start and stop of detected pesense.
        Param:    gpio_pin_pir     -> Type: Integer, Value: Controller's GPIO PIN
        Return:   none
        Modified: 04.02.2018
        """
        global DB_HOST
        global DB_PORT
        global DB_NAME
        global DB_USER
        global DB_PASS

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(gpio_pin_pir, GPIO.IN)

        threading.Thread.__init__(self)

        self.CLASS = "MotionRecorder"
        self.dao = DatabaseDAO(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS)

        self.gpio_pin_pir = gpio_pin_pir

        # Set some defaults
        self.running = True
        self.allowed_silence = 1800
        self.motion_ranking = 0
        self.motion_first = 0
        self.motion_last = 0

        # While motion_lock is bigger than zero we prevent from firing write to the database.
        # This is to avoid flooding the database with unnecessary data (on every PIR activation)
        self.motion_lock = int(self.dao.get_property("motionAllowedSilence")) * 60

    def run(self):
        """
        Name:     run()
        Desc:     Thread recording motions in the database
        Param:    none
        Return:   none
        Modified: 04.02.2018
        """
        logger(LOG_SINK, FINE, self.CLASS, "Motion recording listener started: pir[{}], allowed_silence[{}]."
               .format(self.gpio_pin_pir, self.allowed_silence))

        try:
            GPIO.add_event_detect(self.gpio_pin_pir, GPIO.RISING, callback=self.motionDetected)

            while self.running:
                self.motion_lock += 1
                time.sleep(1)
        finally:
            GPIO.cleanup()

    def motionDetected(self, pin):
        """
        Name:     motionDetected()
        Desc:     Sets the time in seconds on how often to check and record the temperature
        Param:    none
        Return:   none
        Modified: 04.02.2018
        """
        motion_allowed_silence = self.dao.get_property("motionAllowedSilence")
        motion_time_between_writes = self.dao.get_property("motionTimeBetweemWrites")

        self.motion_ranking += 1
        motion_now = time.time()

        logger(LOG_SINK, FINEST, self.CLASS,
               "Detected motion on pin {}: motion_first[{}], motion_last[{}], motion_now[{}], silent_until[{}], currentLockBetweenWritesDuration[{}]."
               .format(self.gpio_pin_pir, self.motion_first, self.motion_last, motion_now,
                       self.motion_last + motion_allowed_silence * 60, self.motion_lock))

        if self.motion_first == 0 or ((self.motion_lock >= motion_time_between_writes) and (
                motion_now > (self.motion_last + motion_allowed_silence * 60))):
            # This is the first time we detect a motion OR
            # We record an end presence only if the occupant's last motion in the premise was LESS than settings.motionAllowedSilence ago.
            self.motion_ranking = 1
            self.motion_first = motion_now
            logger(LOG_SINK, FINER, self.CLASS,
                   "Setting first motion: motionNow[{}], settings.motionAllowedSilence[{}], staySilentUntil[{}], settings.motionTimeBetweenWrites[{}], currentLockBetweenWritesDuration[{}]."
                   .format(timestampToDatetime(motion_now), motion_allowed_silence,
                           timestampToDatetime(motion_now + motion_allowed_silence * 60), motion_time_between_writes,
                           self.motion_lock))
        elif self.motion_lock < motion_time_between_writes:
            # We skip write if we have already writen less than settings.motionTimeBetweemWrites minutes ago.
            logger(LOG_SINK, FINER, self.CLASS,
                   "Skipping motion write as it was sooner than the settings.motionTimeBetweemWrites[{}] seconds ago. LastWrite[{}], Now[{}], currentLockBetweenWritesDuration[{}]"
                   .format(motion_time_between_writes, timestampToDatetime(self.motion_last),
                           timestampToDatetime(motion_now), self.motion_lock))
            return None

        self.motion_lock = 0
        self.motion_last = motion_now

        logger(LOG_SINK, FINER, self.CLASS,
               "Setting last detected motion to: {}".format(timestampToDatetime(self.motion_last)))

        self.dao.save_motion(self.gpio_pin_pir, self.motion_first, self.motion_last, self.motion_ranking)

    def stop(self):
        """
        Name:     stop
        Desc:     Terminates the motion recorder
        Param:    none
        Return:   none
        Modified: 04.02.2018
        """
        logger(LOG_SINK, FINER, self.CLASS, "Stopping motion recorder..")
        self.running = False
