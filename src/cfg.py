import hashlib
import subprocess

class Cfg:

    # all uv4l and Janus settings created during setup of a stream
    dict = {}

    DISPLAY_NAME = "LeasCrib"
    TEMPERATURE = False
    URL_UV4L = "https://localhost:8889/api/janus/client"
    URL_JANUS = "https://www.jasconcept.com:8089/janus"
    HEADERS = {'Content-type': 'application/json'}
    PI_SERIAL = subprocess.run(["printf $(vcgencmd otp_dump | grep '28:')"], check=True, stdout=subprocess.PIPE, universal_newlines=True, shell=True).stdout.strip()
    AUTH_TOKEN = hashlib.sha256(PI_SERIAL.encode()).hexdigest()
