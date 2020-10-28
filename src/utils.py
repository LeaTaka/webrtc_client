import subprocess
import random
import string
import os
from w1thermsensor import W1ThermSensor as w1
from src.cfg import Cfg
from src import apa102

os.chdir(os.path.join('/home/pi/webrtc_client/'))

# Check if the internet connection is down by sending a single ping to Google each iteration
def internet_connection_is_up():
    if subprocess.call("ping -c 1 8.8.8.8 > /dev/null 2>&1", shell=True) == 0:
        # apa102.led_set("off", "off", "off")
        return True
    else:
        print('Internet connection is down! Trying to connect ... .   .      .           .')
        apa102.led_set("off", "magenta", "off")
        return False


# Try to get the temperature
def get_temp():
    if Cfg.TEMPERATURE:
        try:
            return round((w1().get_temperature()), 1)
        except:
            pass


# A random number is used for generating a transaction_id and feed_id
def random_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# Shutdown the machine
def shutdown():
    subprocess.call("sudo shutdown -r now", shell=True)