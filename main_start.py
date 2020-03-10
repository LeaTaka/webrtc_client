#!/usr/bin/env python3

import sys
import RPi.GPIO as GPIO
import requests
from time import sleep
from src import apa102, uv4l, janus, etc, button
from requests.packages.urllib3.exceptions import SubjectAltNameWarning
# Disable warnings for SecurityWarning: Certificate has no `subjectAltName`, RFC 2818
requests.packages.urllib3.disable_warnings(SubjectAltNameWarning)

# Setup GPIO17 as input with internal pull-up resistor to hold it HIGH
# until it is pulled down to GND by the connected button: 
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Register an edge detection event on FALLING edge. When this event
# fires, the callback onButton() will be executed. Because of
# bouncetime=20 all edges 20 ms after a first falling edge will be ignored:
GPIO.add_event_detect(17, GPIO.FALLING, callback=button.on_pull, bouncetime=200)

# manual start through leaM.service
try:
    if sys.argv[1] == "start":
        print("Fantastic!! Go Go Gadget Manual .. !")
except:
    pass


# initiate infinite loop
apa102.led_set("magenta", "magenta", "magenta")
sleep(2)
apa102.led_set("off", "off", "off")
recovery_from_internet_disconnect_active = False
while True:
    # Check if we are online!
    if etc.internet_connection_is_up():
        if button.s_streaming and recovery_from_internet_disconnect_active:
            # after an internet disconnect, a room and pin still exist.
            # Making sure that this data is used for a reconnect.
            orphaned_room = button.s_streaming["room"]
            orphaned_pin = button.s_streaming["pin"]
            print('We have an orphaned room ({}) with pin {}, available on this session'.format(orphaned_room, orphaned_pin))
            # try to reconnect with the previous created room & pin
            button.s_streaming = uv4l.start_streaming(orphaned_room, orphaned_pin)
            # in case of failure, continue trying to establish a stream for 5 times
            button.s_streaming = uv4l.retry_start_streaming(button.s_streaming, orphaned_room, orphaned_pin)
            apa102.led_set("off", "off", "off")
        if recovery_from_internet_disconnect_active:
            print("System is back online ㋡")
            recovery_from_internet_disconnect_active = False
        if button.s_streaming:
            # Send data to socket
            apa102.led_set("off", "blue", "off")
            temperature = etc.get_temp()
            feed_id = button.s_streaming["feed_id"]
            uv4l.send_to_socket(temperature, feed_id)
    else:
        recovery_from_internet_disconnect_active = True
    sleep(15)
