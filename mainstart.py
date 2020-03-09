#!/usr/bin/env python3

import time
from src import apa102

# subprocess related
import subprocess
# hash related
import hashlib
# gpio related
import RPi.GPIO as GPIO
# janus & uv4l
import requests
from requests.packages.urllib3.exceptions import SubjectAltNameWarning

requests.packages.urllib3.disable_warnings(SubjectAltNameWarning)
from requests.exceptions import Timeout
import json
import random
import string
## open socket
import sys
import os
import socket
## ds18b20
from w1thermsensor import W1ThermSensor as w1

sys.path.append("/home/pi/webrtcClient")
cfg = json.load(open('/home/pi/webrtcClient/cfg.json'))


# Try to get the temperature
def gettemp():
    if cfg['temperature'] != "no":
        try:
            temp = round((w1().get_temperature()), 1)
            return temp
        except:
            pass


# Create a socketconnection
def createSocketConnection():
    if cfg['temperature'] != "no":
        print(cfg['temperature'])
        socket_path = '/tmp/uv4l.socket'
        try:
            os.unlink(socket_path)
        except:
            if os.path.exists(socket_path):
                raise
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        print('Socket path: {0}'.format(socket_path))
        s.bind(socket_path)
        s.listen(1)
        print('Awaiting socket connection...')
        connection, client_address = s.accept()
        print('Socket connected')
        print('Established connection with client')
        return connection


# Send data to socket
def sendToSocket():
    if cfg['temperature'] != "no":
        apa102.led_set("off",  "blue", "off")
        data = '{"temp": "' + str(gettemp()) + '", "id": "' + str(feed_id) + '"}'
        print(data)
        connection.send(str(data).encode())


# Check internet connection
def checkInternetConn():
    internetconnection = subprocess.call("ping -c 1 8.8.8.8 > /dev/null 2>&1", shell=True)
    return internetconnection


# Define a function to keep script running
def mainLoop():
    import signal
    # Turn on the 3x LED red in boot state
    apa102.led_set("magenta", "magenta", "magenta")

    time.sleep(2)
    # And then check the response...
    response = 1
    # Set socketvalidation global & to 0
    global socketvalidation
    # global temp
    global feed_id
    global connection
    global room
    global pin
    internet = 0
    socketvalidation = 0
    while True:
        # Turn off the LED to indicate stopped/ready to start
        # Check if we are online!
        if checkInternetConn() == 0:
            if internet == 404 and int(socketvalidation) > 0:
                print(
                    'Internet connection is down! Trying to reconnect to {0}... .   .      .           .'.format(room))
                orphanedroom = room
                orphanedpin = pin
                mediaStream(orphanedroom, orphanedpin)
            # reset internet to zero (= online) 
            internet = 0

            apa102.led_set("off", "off", "off")

            # open socket only one time during session!!
            if int(socketvalidation) > 1:
                connection = createSocketConnection()
                feed_id = socketvalidation
                socketvalidation = 1
            # loop data over socket during session
            if int(socketvalidation) == 1:

                apa102.led_set("off", "blue", "off")

                # Send data to socket
                sendToSocket()
        else:
            apa102.led_set("off", "magenta", "off")
            internet = 404
        time.sleep(28)


# Define a callback function that will be called by the GPIO
# event system:
def onButton(channel):
    global room
    global socketvalidation
    if channel == 17:
        start_time = time.time()
        while GPIO.input(channel) == 0:
            buttonTime = time.time() - start_time
            if 1 <= buttonTime <= 10:

                apa102.led_set("blue", "blue", "blue")

                if GPIO.input(channel) == 1:
                    uv4lstatus = subprocess.run(["pidof uv4l"], stdout=subprocess.PIPE, universal_newlines=True,
                                                shell=True).stdout.strip()
                    try:
                        if not uv4lstatus:
                            while int(socketvalidation) == 0:
                                socketvalidation = mediaStream()
                                if int(socketvalidation) == 0:
                                    print('Join room failed, one more try to join the room')
                            # set to 0 when there is a big error (missing apitoken/secret?)
                            if int(socketvalidation) == -1:
                                socketvalidation = 0
                                apa102.led_set("blue", "magenta", "blue")
                            apa102.led_fade_in("green", "green", "green")
                            apa102.led_fade_out("green", "green", "green")
                            apa102.led_set("off", "green", "off")
                        else:
                            apa102.led_set("blue", "blue", "blue")

                            socketvalidation = mediaStreamDestroy(transaction, room, session_id, plugin_id)
                            apa102.led_set("off", "off", "off")

                            # set to zero in order to forget the number after an internet disconnect
                            room = 0
                    except OSError as e:
                        print(sys.stderr, "Execution failed:", e)
                    return socketvalidation
            elif buttonTime > 10:
                apa102.led_set("white", "white", "white")

                subprocess.call("sudo shutdown -r now", shell=True)


## INIT JANUS STREAM
def mediaStream(orphanedroom=0, orphanedpin=''):
    global transaction
    global room
    global session_id
    global plugin_id
    global token
    global room
    global pin
    global urlJanus
    global headers
    global urlUv4l
    piserial = subprocess.run(["printf $(vcgencmd otp_dump | grep '28:')"], check=True, stdout=subprocess.PIPE,
                              universal_newlines=True, shell=True).stdout.strip()
    token = hashlib.sha256(piserial.encode()).hexdigest()
    displayname = "LeasCrib"
    urlUv4l = cfg['urlUv4l']
    urlJanus = cfg['urlJanus']
    headers = {'Content-type': 'application/json', }

    ##DESTROY JANUS SESSION & UV4L IF ANY
    uv4lstatus = subprocess.run(["pidof uv4l"], stdout=subprocess.PIPE, universal_newlines=True,
                                shell=True).stdout.strip()
    try:
        if uv4lstatus:
            print('Terminating uv4l PID {0} through shell...'.format(uv4lstatus))
            data = '{"what": "destroy", "plugin": "videoroom","transaction": ""}'
            response = requests.post(urlUv4l, headers=headers, data=data,
                                     verify='/home/pi/webrtcClient/cert/server.pem')
            result = json.loads(response.content.decode('ascii'))
            if result["what"] == 'error':
                print(result["error"]["reason"])
            else:
                print('{0}fully destroyed session'.format(result["what"]))
            subprocess.run(["sudo pkill uv4l"], shell=True)
    except OSError as e:
        print(sys.stderr, "Execution failed:", e)
    time.sleep(0.5)

    ##STARTUP UV4L with configuration parameters
    subprocess.call("\
    uv4l --auto-video_nr --driver dummy --frame-buffers=2 \
    --server-option '–-bind-host-address=localhost' \
    --server-option '--port=8889' \
    --server-option '--use-ssl=yes' \
    --server-option '--ssl-private-key-file=/home/pi/webrtcClient/cert/server.key' \
    --server-option '--ssl-certificate-file=/home/pi/webrtcClient/cert/server.pem' \
    --server-option '--enable-webrtc=yes' \
    --server-option '--enable-webrtc-video=no' \
    --server-option '--webrtc-receive-video=no' \
    --server-option '--enable-webrtc-audio=yes' \
    --server-option '--webrtc-receive-audio=no' \
    --server-option '--webrtc-recdevice-index=3' \
    --server-option '--webrtc-vad=yes' \
    --server-option '--webrtc-echo-cancellation=yes' \
    --server-option '--enable-webrtc-datachannels=yes' \
    --server-option '--webrtc-datachannel-label=uv4l' \
    --server-option '--webrtc-datachannel-socket=/tmp/uv4l.socket' \
    --server-option '--janus-gateway-url=https://www.jasconcept.com:8089' \
    ", shell=True)
    time.sleep(0.5)  # uv4l needs some time for its multiple processes..

    ##GENERATE TRANSACTIONID & FEEDID FOR JANUS
    def randomGenerator(size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    transaction = randomGenerator(40)
    feed_id = ''.join(filter(str.isdigit, transaction))
    print('Serial#         = {0}'.format(piserial))
    print('Transactionid   = {0}'.format(transaction))
    print('Feed_id         = {0}'.format(feed_id))

    ##CREATE SESSION
    # first set the uv4l settings for inserting the token
    data = '{"gateway":{"apisecret":"","auth_token":"' + token + '","root":"/janus","url":"' + urlJanus + '"},"http_proxy":{"host":"","non_proxy_hosts_regex":"","password":"","port":80,"user":""},"session":{"reconnect_delay_s":3,"reconnect_on_failure":true},"videoroom":{"as_listener":{"audio":false,"data":false,"video":false},"as_publisher":{"adjust_max_bitrate_for_hardware_videocodec":true,"audio":true,"data":true,"max_bitrate_bits":0,"rec_filename":"myrecording","record":false,"use_hardware_videocodec":false,"video":true,"video_format_id":60},"audiocodec":"opus","fir_freq":0,"is_private":false,"max_bitrate_for_publishers_bits":128000,"max_listeners":3,"max_publishers":6,"permanent":false,"rec_dir":"/usr/share/janus/recordings/","record":false,"room":1234,"room_description":"","room_pin":"","room_secret":"","username":"","videocodec":"vp8"}}'
    response = requests.put(urlUv4l + "/settings", headers=headers, data=data,
                            verify='/home/pi/webrtcClient/cert/server.pem')
    result = json.loads(response.content.decode('ascii'))
    print('Uv4l settings   = {0}'.format(result["response"]["reason"]))
    # sessionstart
    data = '{"what": "create", "plugin": "videoroom", "transaction": "' + transaction + '"}'
    response = requests.post(urlUv4l, headers=headers, data=data, verify='/home/pi/webrtcClient/cert/server.pem')
    result = json.loads(response.content.decode('ascii'))
    if result["what"] == 'error':
        print('Failed. {0}'.format(result["error"]["reason"]))
        ##destroy uv4l process in case of error. socketvalidation = -1 for disabling all following actions
        print('Terminating uv4l through shell...')
        subprocess.run(["sudo pkill uv4l"], shell=True)
        return -1
    else:
        session_id = result["session_id"]
        plugin_id = result["plugins"][0]["id"]
        print('Create session  = {0}'.format(result["what"]))
        print('Sessionid       = {0}'.format(result["session_id"]))
        print('Pluginid        = {0}'.format(result["plugins"][0]["id"]))

    if orphanedroom == 0 and orphanedpin == '':
        ##CHECK ROOM NUMBER
        data = '{"janus": "message", "transaction": "' + transaction + '", "token": "' + token + '", "body": {"request": "list"}}'
        response = requests.post(urlJanus + "/" + session_id + "/" + plugin_id, headers=headers, data=data, verify=True)
        result = json.loads(response.content.decode('ascii'))
        rooms = [(list['room']) for list in result["plugindata"]["data"]["list"]]
        print('Number of rooms = {}'.format(len(rooms)))
        # print('Available rooms = {0}'.format(str(rooms)[1:-1]))

        room = (feed_id.strip("0") * 5)[:5]
        pin = (feed_id.strip("0") * 4)[-4:]
        while True:
            if room in set(rooms):
                room = int(randomGenerator(5, "1234567890").strip("0"))
                continue
            else:
                room = str(room)
                break

        ##CREATE ROOM
        data = '{"janus": "message", "transaction": "' + transaction + '", "token": "' + token + '", "body": {"request": "create", "audiocodec": "opus", "bitrate": 128000, "description": "Pretty room", "fir_freq": 10, "notify_joining": false, "record": false, "require_pvtid": false, "room": ' + room + ', "pin": "' + pin + '", "videocodec": "h264", "audiolevel_event": true, "audio_active_packets": 100, "audio_level_average": 25}}'
        response = requests.post(urlJanus + "/" + session_id + "/" + plugin_id, headers=headers, data=data, verify=True)
        result = json.loads(response.content.decode('ascii'))
        if result["plugindata"]["data"]["videoroom"] == "event":
            print(result["plugindata"]["data"]["error"])
        else:
            print('Room created    = success ({0} / {1})'.format(room, pin))
    else:
        room = orphanedroom
        pin = orphanedpin

    ##JOIN ROOM
    auth_string = '{{\\"displayname\\":\\"{0}\\",\\"piserial\\":\\"{1}\\",\\"room\\":\\"{2}\\",\\"pin\\":\\"{3}\\"}}'.format(
        displayname, piserial, room, pin)
    data = '{"janus": "message", "transaction": "' + transaction + '", "token": "' + token + '", "body": {"request": "join", "ptype": "publisher", "room": ' + room + ', "pin": "' + pin + '", "id": ' + feed_id + ', "display": "' + auth_string + '"}}'
    response = requests.post(urlJanus + "/" + session_id + "/" + plugin_id, headers=headers, data=data, verify=True)
    result = json.loads(response.content.decode('ascii'))
    print('Join room       = {0} ({1})'.format(result["janus"], room))
    if result["janus"] == "error":
        return 0

    ##SUBSCRIBE MEDIA
    data = '{"what": "publish", "transaction": "' + transaction + '", "body": {"audio": true, "video": false, "data": true, "adjust_max_bitrate_for_hardware_videocodec": true, "max_bitrate_bits": 0, "use_hardware_videocodec": false, "video_format_id": 60, "record": false, "rec_filename": "myrecording"}}'
    response = requests.post(urlUv4l + "/videoroom", headers=headers, data=data,
                             verify='/home/pi/webrtcClient/cert/server.pem')
    result = json.loads(response.content.decode('ascii'))
    print('Subscribe media = {0}'.format(result["what"]))

    return feed_id


##TERMINATE JANUS ROOM & SESSION
def mediaStreamDestroy(transaction, room, session_id, plugin_id):
    uv4lstatus = subprocess.run(["pidof uv4l"], stdout=subprocess.PIPE, universal_newlines=True,
                                shell=True).stdout.strip()
    try:
        if uv4lstatus:
            # unpublish media
            data = '{"janus":"message","transaction":"' + transaction + '","token":"' + token + '","body":{"request":"unpublish"}}'
            response = requests.post(urlJanus + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                                     verify=True)
            result = json.loads(response.content.decode('ascii'))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            if result["janus"] == 'error':
                print(result["error"]["reason"])
            else:
                print('Unpublish media = {0}'.format(result["janus"]))
            # destroy room
            data = '{"janus": "message", "transaction": "' + transaction + '", "token": "' + token + '", "body": {"request": "destroy", "room": ' + room + '}}'
            response = requests.post(urlJanus + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                                     verify=True)
            result = json.loads(response.content.decode('ascii'))
            if result["janus"] == 'error':
                print(result["error"]["reason"])
            else:
                print('Destroy room    = {0} ({1})'.format(result["janus"], room))
            # destroy janus session & uv4l
            data = '{"what": "destroy", "plugin": "videoroom","transaction": "' + transaction + '"}'
            response = requests.post(urlUv4l, headers=headers, data=data,
                                     verify='/home/pi/webrtcClient/cert/server.pem')
            result = json.loads(response.content.decode('ascii'))
            print('Destroy session = {0}'.format(result["what"]))
            print('Terminating uv4l PID {0} through shell...'.format(uv4lstatus))
            subprocess.run(["sudo pkill uv4l"], shell=True)
            return 0
    except OSError as e:
        print(sys.stderr, "DESTROY Execution failed:")  # , e)


##TERMINATE JANUS SESSION FROM SERVICE
def mediaStreamDestroyService():
    urlUv4l = cfg['urlUv4l']
    headers = {'Content-type': 'application/json', }
    uv4lstatus = subprocess.run(["pidof uv4l"], stdout=subprocess.PIPE, universal_newlines=True,
                                shell=True).stdout.strip()
    # print(uv4lstatus)
    try:
        if uv4lstatus:
            data = '{"what": "destroy", "plugin": "videoroom","transaction": ""}'
            response = requests.post(urlUv4l, headers=headers, data=data,
                                     verify='/home/pi/webrtcClient/cert/server.pem')
            result = json.loads(response.content.decode('ascii'))
            if result["what"] == 'error':
                print(result["error"]["reason"])
            else:
                print('Session destroyed = {0}'.format(result["what"]))
            subprocess.run(["sudo pkill uv4l"], shell=True)
            return 0
    except OSError as e:
        print(sys.stderr, "DESTROY Execution failed:", e)


# Setup GPIO17 as input with internal pull-up resistor to hold it HIGH
# until it is pulled down to GND by the connected button: 
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Register an edge detection event on FALLING edge. When this event
# fires, the callback onButton() will be executed. Because of
# bouncetime=20 all edges 20 ms after a first falling edge will be ignored: 
GPIO.add_event_detect(17, GPIO.FALLING, callback=onButton, bouncetime=200)

# Main program
if sys.argv[1] == "start":
    mainLoop()
elif sys.argv[1] == "stop":
    apa102.led_set("off", "off", "off")
    mediaStreamDestroyService()
elif sys.argv[1] == "startManual":
    apa102.led_set("off", "off", "off")
    mediaStream()
elif sys.argv[1] == "stopManual":
    apa102.led_set("off", "off", "off")
    mediaStreamDestroyService()