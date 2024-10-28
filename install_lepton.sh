#!/bin/bash

# Stop on error
set -e

# Giving permission to usb devices through libusb
LEPTON_VID=1e4e
LEPTON_PID=0100
echo "ATTRS{idVendor}==\"$LEPTON_VID\", ATTRS{idProduct}==\"$LEPTON_PID\", MODE=\"0666\"" | sudo tee /etc/udev/rules.d/60-purethermal.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# Open CV dependences
sudo apt-get -y install libatlas-base-dev

# libuvc library -> IR sensor
sudo apt install -y cmake libusb-1.0-0-dev libjpeg-dev zlib1g-dev libpng-dev
git clone https://github.com/groupgets/libuvc && cd libuvc && mkdir build && cd build && cmake .. && make && sudo make install && sudo ldconfig -v && cd ../../ && rm -rf libuvc
