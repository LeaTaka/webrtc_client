from time import time
from src import connection_manager
import RPi.GPIO as GPIO


class Button:

    initial_status = "disabled"
    requested_status = initial_status

    def on_pull(self, channel):
        start_time = time()
        while GPIO.input(channel) == 0:
            button_time = time() - start_time
            if 1 <= button_time <= 10:
                if GPIO.input(channel) == 1:
                    if GPIO.input(channel) == 1 and self.requested_status == "disabled":
                        self.requested_status = "active"
                    elif GPIO.input(channel) == 1 and self.requested_status == "active":
                        self.requested_status = "disabled"
