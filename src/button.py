from time import time
from src import apa102, utils
import RPi.GPIO as GPIO


class Button:

    initial_status = "disabled"
    requested_status = initial_status

    def on_pull(self, channel):
        start_time = time()
        while GPIO.input(channel) == 0:
            button_time = time() - start_time
            if 1 <= button_time <= 10:
                apa102.led_set("blue", "blue", "blue")
                if GPIO.input(channel) == 1:
                    if GPIO.input(channel) == 1 and self.requested_status == "disabled":
                        self.requested_status = "active"
                    elif GPIO.input(channel) == 1 and self.requested_status == "active":
                        self.requested_status = "disabled"
            elif button_time > 10:
                # reboot the system after having hold the button for longer than 10 seconds
                apa102.led_set("white", "white", "white")
                utils.shutdown()
