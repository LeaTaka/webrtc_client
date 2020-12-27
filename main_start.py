#!/usr/bin/python3

from time import sleep

import RPi.GPIO as GPIO
from src import utils
from src.cfg import Cfg
from src.connection_manager import ConnectionManager
from src.button import Button

button = Button()
cfg = Cfg()
connection_manager = ConnectionManager(cfg)

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(17, GPIO.FALLING, callback=button.on_pull, bouncetime=200)


while True:
    status = button.requested_status
    internet = utils.internet_connection_is_up()

    # print(f"Device set to be: {status}" )

    connection_manager.ensure_status(status, internet)

    sleep(1)
