import requests
import json
import sys
import os
from src import uv4l, etc, button

os.chdir(os.path.join('/home/pi/webrtc_client/'))
cfg = json.load(open('cfg.json'))
headers = {'Content-type': 'application/json'}


# choose a random room number and check if it exists, continue until a unique number is found
def select_room_number(feed_id, transaction_id, session_id, plugin_id):
    data = '{"janus": "message", "transaction": "' + transaction_id + '", "token": "' + button.AUTH_TOKEN + '", "body": {"request": "list"}}'
    response = requests.post(cfg['url_janus'] + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                             verify=True)
    result = json.loads(response.content.decode('ascii'))
    rooms = [(list['room']) for list in result["plugindata"]["data"]["list"]]
    print('Number of rooms = {}'.format(len(rooms)))
    # print('Available rooms = {0}'.format(str(rooms)[1:-1]))

    room = (feed_id.strip("0") * 5)[:5]
    while True:
        if room in set(rooms):
            room = int(etc.random_generator(5, "1234567890").strip("0"))
            continue
        else:
            return str(room)


def create_room(feed_id, transaction_id, session_id, plugin_id, room):
    pin = (feed_id.strip("0") * 4)[-4:]
    data = '{"janus": "message", "transaction": "' + transaction_id + '", "token": "' + button.AUTH_TOKEN + '", "body": {"request": "create", "audiocodec": "opus", "bitrate": 128000, "description": "Pretty room", "fir_freq": 10, "notify_joining": false, "record": false, "require_pvtid": false, "room": ' + room + ', "pin": "' + pin + '", "videocodec": "h264", "audiolevel_event": true, "audio_active_packets": 100, "audio_level_average": 25}}'
    response = requests.post(cfg['url_janus'] + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                             verify=True)
    result = json.loads(response.content.decode('ascii'))
    if result["plugindata"]["data"]["videoroom"] == "event":
        print(result["plugindata"]["data"]["error"])
        return False
    else:
        print('Room created    = success ({0} / {1})'.format(room, pin))
        return pin


def join_room(feed_id, transaction_id, session_id, plugin_id, room, pin):
    auth_string = '{{\\"display_name\\":\\"{0}\\",\\"pi_serial\\":\\"{1}\\",\\"room\\":\\"{2}\\",\\"pin\\":\\"{3}\\"}}'.format(
        button.DISPLAY_NAME, button.PI_SERIAL, room, pin)
    data = '{"janus": "message", "transaction": "' + transaction_id + '", "token": "' + button.AUTH_TOKEN + '", "body": {"request": "join", "ptype": "publisher", "room": ' + room + ', "pin": "' + pin + '", "id": ' + feed_id + ', "display": "' + auth_string + '"}}'
    response = requests.post(cfg['url_janus'] + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                             verify=True)
    result = json.loads(response.content.decode('ascii'))
    if result["janus"] == "ack":
        print('Join room       = {0} ({1} / {2})'.format(result["janus"], room, pin))
        return True
    else:
        print('Join room failed, one more try to join the room')
        return False


# clean up, so no orphaned rooms will exist
def destroy_room(transaction_id, session_id, plugin_id, room):
    try:
        data = '{"janus": "message", "transaction": "' + transaction_id + '", "token": "' + button.AUTH_TOKEN + '", "body": {"request": "destroy", "room": ' + room + '}}'
        response = requests.post(cfg['url_janus'] + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                                 verify=True)
        result = json.loads(response.content.decode('ascii'))
        if result["janus"] == 'error':
            print(result["error"]["reason"])
            return False
        else:
            print('Destroy room    = {0} ({1})'.format(result["janus"], room))
            return True
    except OSError as e:
        print(sys.stderr, "Destroy room failed:")  # , e)


# remove your media from the stream
def unpublish_media(transaction_id, session_id, plugin_id, room):
    try:
        data = '{"janus":"message","transaction":"' + transaction_id + '","token":"' + button.AUTH_TOKEN + '","body":{"request":"unpublish"}}'
        response = requests.post(cfg['url_janus'] + "/" + session_id + "/" + plugin_id, headers=headers, data=data,
                                 verify=True)
        result = json.loads(response.content.decode('ascii'))
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        if result["janus"] == 'error':
            print(result["error"]["reason"])
        else:
            print('Unpublish media = {0}'.format(result["janus"]))
        destroy_room(transaction_id, session_id, plugin_id, room)
        uv4l.destroy_uv4l_processes_if_any()
        # set s_streaming to False with output: no streaming sessions active and back to ready for start_processes()
        return False
    except OSError as e:
        print(sys.stderr, "Unpublish media failed:")
