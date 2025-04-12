#! /bin/sh
export BHOME=/opt/boilerry
############################################################
# SSH and WiFi should be enabled during the SD Card flashing.
############################################################


############################################################
# Execute `sudo raspi-config` to enable 1-Wire in the Kernel
#	- 1-Wire
# 
# In addition, enable the 1-wire on the specific GPIO pins
# that a peripherial device is connected.
# ----------------------------------------------------------
sudo raspi-config
sudo sed -i $'s/.*dtoverlay=w1-gpio.*/dtoverlay=w1-gpio,gpiopin=17\\\ndtoverlay=w1-gpio,gpiopin=27/g' /boot/firmware/config.txt


############################################################
# Increase the security by changing the SSH port to 9722.
# ----------------------------------------------------------
sudo vi /etc/ssh/sshd_config


############################################################
# Upgrade the O/S as follows
# ----------------------------------------------------------
sudo apt-get update
sudo apt-get upgrade
sudo apt-get --assume-yes install git

############################################################
# Insert the Copyright message
# ----------------------------------------------------------
sudo tee /etc/motd <<EOF
============================== I AM SO HOT  ==============================
 This is private system of Kliment Stefanov. All access to this system is
 strictly prohibited and any offenders will be prosecuted.
 All rights reserved.
=========================== boilerry.vayak.com ===========================
EOF


############################################################
# Create the Boilerry environment
# ----------------------------------------------------------
sudo mkdir -p $BHOME/python && cd $BHOME
sudo chmod -R pimmy:pimmy $BHOME


############################################################
# Install the Python 3.11 virtual environment for Boilerry
# ----------------------------------------------------------
sudo apt-get --assume-yes install python3-pip
python3 -m venv $BHOME/python
$BHOME/python/bin/pip install DBUtils
$BHOME/python/bin/pip install pymysql
$BHOME/python/bin/pip install python-dateutil
$BHOME/python/bin/pip install requests
$BHOME/python/bin/pip install RPi.GPIO
$BHOME/python/bin/pip install websockets


############################################################
# Download the Boilerry repository
# ----------------------------------------------------------
git clone https://github.com/pimmygit/boilerry-server.git


############################################################
# Install MySQL (MariaDB)
# Root: L3bl3b1a!
# ----------------------------------------------------------
sudo apt-get --assume-yes install mariadb-server
sudo mysql_secure_installation
mysql -u root -p < $BHOME/boilerry-server/create_databasa.sql

sudo reboot
