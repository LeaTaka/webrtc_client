# webrtcClient for Buster

## HW prerequisites:
* [PI Zero WH (others not tested)](https://www.raspberrypi.org/products/raspberry-pi-zero/)
* [ReSpeaker 2-Mics Pi HAT](http://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/) - the mics
* [DS18B20 sensor (optional)](https://www.seeedstudio.com/DS18B20-Temperature-Sensor-Waterproof-Probe-p-4283.html) - Measure and report the temperature

## Software installed by ./configure
* [Uv4l](https://www.linux-projects.org/uv4l/installation/)
* [ReSpeaker driver](https://github.com/respeaker/seeed-voicecard/)
* [Raspap](https://github.com/billz/raspap-webgui) - Wifi configuration portal

## Install for Rpi0 (others not tested, install time approx. 1 hour!):
Run ./configure
A dist-upgrade will be executed. If a reboot is automatically initiated, just run .configure again.
Make sure to use a clean buster image