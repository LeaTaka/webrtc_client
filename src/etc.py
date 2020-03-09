# Check internet connection
import subprocess
import json
import random
import string
import os
from w1thermsensor import W1ThermSensor as w1
from src import apa102

os.chdir(os.path.join('/home/pi/webrtc_client/'))
cfg = json.load(open('cfg.json'))


# Check if the internet connection is down by sending a single ping to Google each iteration
def internet_connection_is_up():
    if subprocess.call("ping -c 1 8.8.8.8 > /dev/null 2>&1", shell=True) == 0:
        return True
    else:
        print('Internet connection is down! Trying to reconnect ... .   .      .           .')
        apa102.led_set("off", "magenta", "off")
        return False


# Try to get the temperature
def get_temp():
    if cfg['temperature']:
        try:
            return round((w1().get_temperature()), 1)
        except:
            pass


# A random number is used for generating a transaction_id and feed_id
def random_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# Get the hardware serial number from the raspberry pi
def pi_serial():
    return subprocess.run(["printf $(vcgencmd otp_dump | grep '28:')"], check=True, stdout=subprocess.PIPE,
                          universal_newlines=True, shell=True).stdout.strip()


# Shutdown the machine
def shutdown():
    subprocess.call("sudo shutdown -r now", shell=True)
