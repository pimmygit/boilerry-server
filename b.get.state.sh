#! /bin/sh

export BHOME=/opt/boilerry

sudo python3 -c "from GPIO import *; go = GPIO(); print(go.getHeatingState())"
