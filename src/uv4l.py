# Create a socket connection
import os
import sys
import socket
from src import apa102, janus, etc, button
from time import sleep
import json
import subprocess
import requests

os.chdir(os.path.join('/home/pi/webrtc_client/'))
cfg = json.load(open('cfg.json'))
headers = {'Content-type': 'application/json'}


def create_socket_connection():
    if cfg['temperature']:
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
        print(connection)
        return connection


def send_to_socket(temp, feed_id):
    if cfg['temperature']:
        # open socket only one time during session!!
        while not create_socket_connection():
            pass
        apa102.led_set("off", "blue", "off")
        data = '{"temp": "' + str(temp) + '", "id": "' + str(feed_id) + '"}'
        print(data)
        connection.send(str(data).encode())


# check if a uv4l process is active
def status():
    return subprocess.run(["pidof uv4l"], stdout=subprocess.PIPE, universal_newlines=True, shell=True).stdout.strip()


# destroy all multiple uv4l processes
def destroy_uv4l_processes_if_any():
    try:
        if status():
            print('Terminating uv4l PID {0} through shell...'.format(status()))
            data = '{"what": "destroy", "plugin": "videoroom","transaction": ""}'
            response = requests.post(cfg['url_uv4l'], headers=headers, data=data,
                                     verify='cert/server.pem')
            result = json.loads(response.content.decode('ascii'))
            if result["what"] == 'error':
                print(result["error"]["reason"])
            else:
                print('{0}fully destroyed session'.format(result["what"]))
            subprocess.run(["sudo pkill uv4l"], shell=True)
    except OSError as e:
        print(sys.stderr, "Execution failed:", e)
    sleep(0.5)


# strat multiple uv4l processes with below configuration
def start_processes():
    subprocess.call("\
    uv4l --auto-video_nr --driver dummy --frame-buffers=2 \
    --server-option '–-bind-host-address=localhost' \
    --server-option '--port=8889' \
    --server-option '--use-ssl=yes' \
    --server-option '--ssl-private-key-file=/home/pi/webrtc_client/cert/server.key' \
    --server-option '--ssl-certificate-file=/home/pi/webrtc_client/cert/server.pem' \
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
    sleep(0.5)  # uv4l needs some time to fire up its multiple processes ..


# prepare uv4l settings with the secret information, which provides access to the janus server
def set_token(auth_token):
    data = '{"gateway":{"apisecret":"","auth_token":"' + auth_token + '","root":"/janus","url":"' + cfg[
        'url_janus'] + '"},"http_proxy":{"host":"","non_proxy_hosts_regex":"","password":"","port":80,"user":""},' \
                       '"session":{"reconnect_delay_s":3,"reconnect_on_failure":true},"videoroom":{"as_listener":{' \
                       '"audio":false,"data":false,"video":false},"as_publisher":{' \
                       '"adjust_max_bitrate_for_hardware_videocodec":true,"audio":true,"data":true,' \
                       '"max_bitrate_bits":0,"rec_filename":"myrecording","record":false,' \
                       '"use_hardware_videocodec":false,"video":true,"video_format_id":60},"audiocodec":"opus",' \
                       '"fir_freq":0,"is_private":false,"max_bitrate_for_publishers_bits":128000,"max_listeners":3,' \
                       '"max_publishers":6,"permanent":false,"rec_dir":"/usr/share/janus/recordings/","record":false,' \
                       '"room":1234,"room_description":"","room_pin":"","room_secret":"","username":"",' \
                       '"videocodec":"vp8"}} '
    response = requests.put(cfg['url_uv4l'] + "/settings", headers=headers, data=data,
                            verify='cert/server.pem')
    result = json.loads(response.content.decode('ascii'))
    print('Uv4l settings   = {0}'.format(result["response"]["reason"]))


def session_start(transaction_id):
    data = '{"what": "create", "plugin": "videoroom", "transaction": "' + transaction_id + '"}'
    response = requests.post(cfg['url_uv4l'], headers=headers, data=data, verify='cert/server.pem')
    result = json.loads(response.content.decode('ascii'))

    if result["what"] == 'error':
        print('Failed. {0}'.format(result["error"]["reason"]))
        print('Terminating uv4l through shell...')
        subprocess.run(["sudo pkill uv4l"], shell=True)
        return False
    else:
        return {'session_id': result["session_id"], 'plugin_id': result["plugins"][0]["id"]}


def subscribe_media(transaction_id):
    data = '{"what": "publish", "transaction": "' + transaction_id + '", "body": {"audio": true, "video": false, "data": true, "adjust_max_bitrate_for_hardware_videocodec": true, "max_bitrate_bits": 0, "use_hardware_videocodec": false, "video_format_id": 60, "record": false, "rec_filename": "myrecording"}}'
    response = requests.post(cfg['url_uv4l'] + "/videoroom", headers=headers, data=data, verify='cert/server.pem')
    result = json.loads(response.content.decode('ascii'))
    print('Subscribe media = {0}'.format(result["what"]))
    if result["what"] == 'ack':
        return True
    else:
        return False


# wrapper function that includes all functions required to start streaming
def start_streaming(auth_token=button.AUTH_TOKEN, pi_serial=button.PI_SERIAL, DISPLAY_NAME=button.DISPLAY_NAME,
                    orphaned_room=0, orphaned_pin=''):
    # for each session we create unique id's
    transaction_id = etc.random_generator(40)
    feed_id = ''.join(filter(str.isdigit, transaction_id))

    # destroy uv4l processes if any
    destroy_uv4l_processes_if_any()
    # fire up uv4l processes
    start_processes()
    # set the secret token for acquiring access to the janus server
    set_token(auth_token)
    # some logging for journalctl
    print('Serial#         = {0}'.format(pi_serial))
    print('Transaction_id  = {0}'.format(transaction_id))
    print('Feed_id         = {0}'.format(feed_id))

    # initiate session & videoroom plugin
    session = session_start(transaction_id)
    session_id = session["session_id"]
    plugin_id = session["plugin_id"]

    print('Create session  = Success')
    print('Sessionid       = {0}'.format(session_id))
    print('Pluginid        = {0}'.format(plugin_id))

    # in case of an orphaned room and pin, for example after an internet disconnect,
    # no new room will be created and the existing room and pin will be recycled.
    if orphaned_room == 0 and orphaned_pin == '':
        room = janus.select_room_number(feed_id, transaction_id, auth_token, session_id, plugin_id)
        pin = janus.create_room(feed_id, transaction_id, auth_token, session_id, plugin_id, room)
    else:
        # apparently there is a reconnect and orphaned an room is available
        room = orphaned_room
        pin = orphaned_pin

    # join the room
    janus.join_room(feed_id, transaction_id, auth_token, session_id, plugin_id, room, pin, DISPLAY_NAME, pi_serial)

    # subscribe your media (cam or mic)
    if subscribe_media(transaction_id):
        # show that we joined and subscribed our media, we are live streaming !
        apa102.led_fade_in("green", "green", "green")
        apa102.led_set("red", "red", "red", 255)
        sleep(0.05)
        apa102.led_fade_out("green", "green", "green")
        apa102.led_set("off", "green", "off")
        return {'transaction_id': transaction_id, 'session_id': session_id, 'plugin_id': plugin_id, 'room': room,
                'pin': pin, 'feed_id': feed_id, 'we_are_streaming': True}
    else:
        # in case of a big error (missing apitoken/secret)
        apa102.led_set("blue", "magenta", "blue")
        return False
