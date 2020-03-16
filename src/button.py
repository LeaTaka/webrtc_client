import hashlib
import sys
import RPi.GPIO as GPIO
from src import apa102, uv4l, janus, etc
from time import time, sleep

DISPLAY_NAME = "LeasCrib"
PI_SERIAL = etc.pi_serial()
AUTH_TOKEN = hashlib.sha256(PI_SERIAL.encode()).hexdigest()

s_streaming = False


# Define a callback function that will be called by the GPIO event system:
def on_pull(channel):
    global s_streaming
    if channel == 17:
        start_time = time()
        # while button is not pushed:
        while GPIO.input(channel) == 0:
            button_time = time() - start_time
            # push the button between 1 and 10 seconds
            if 1 <= button_time <= 10:
                apa102.led_set("blue", "blue", "blue")
                # so in case of a pull up (letting loose the button after pushing it), then:
                if GPIO.input(channel) == 1:
                    # try to check if there is a uv4l process open on the raspberry pi
                    try:
                        if not uv4l.processes():
                            # if no process is open, a stream can be started.
                            # Continue trying to establish a stream for 5 times
                            s_streaming = uv4l.try_start_streaming()
                        else:
                            # if a uv4l process is open, and a pull up after a push of a button has occurred, then
                            # apparently the user wishes to close the connection. This is what we do here:
                            apa102.led_set("blue", "blue", "blue")
                            s_streaming = janus.unpublish_media(s_streaming["transaction_id"],
                                                                s_streaming["session_id"], s_streaming["plugin_id"],
                                                                s_streaming["room"])
                            apa102.led_set("off", "off", "off")
                    except OSError as e:
                        print(sys.stderr, "Execution failed:", e)
            elif button_time > 10:
                # reboot the system after having hold the button for longer than 10 seconds
                apa102.led_set("white", "white", "white")
                etc.shutdown()
