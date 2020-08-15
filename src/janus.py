import requests
import json
import sys
import os
from cfg import Cfg
from src import utils

os.chdir(os.path.join('/home/pi/webrtc_client/'))

class Janus:
    initial_status = "disabled"
    status = initial_status
    counter = 0

    # choose a random room number and check if it exists, continue until a unique number is found
    def select_room_number(self):
        data = '{"janus": "message", "transaction": "' + Cfg.dict[
            "transaction_id"] + '", "token": "' + Cfg.AUTH_TOKEN + '", "body": {"request": "list"}}'
        response = requests.post(
            Cfg.URL_JANUS + "/" + Cfg.dict["session_id"] + "/" + Cfg.dict[
                "plugin_id"], headers=Cfg.HEADERS, data=data,
            verify=True)
        result = json.loads(response.content.decode('ascii'))
        rooms = [(list['room']) for list in result["plugindata"]["data"]["list"]]
        print('Number of rooms = {}'.format(len(rooms)))
        # print('Available rooms = {0}'.format(str(rooms)[1:-1]))
        Cfg.dict["room"] = (Cfg.dict["feed_id"].strip("0") * 5)[:5]
        while True:
            if Cfg.dict["room"] in set(rooms):
                Cfg.dict["room"] = int(utils.random_generator(5, "1234567890").strip("0"))
                continue
            else:
                return str(Cfg.dict["room"])

    def create_room(self):
        Cfg.dict["pin"] = (Cfg.dict["feed_id"].strip("0") * 4)[-4:]
        data = '{"janus": "message", "transaction": "' + Cfg.dict[
            "transaction_id"] + '", "token": "' + Cfg.AUTH_TOKEN + '", "body": {"request": "create", "audiocodec": "opus", "bitrate": 128000, "description": "Pretty room", "fir_freq": 10, "notify_joining": false, "record": false, "require_pvtid": false, "room": ' + \
               Cfg.dict["room"] + ', "pin": "' + Cfg.dict[
                   "pin"] + '", "videocodec": "h264", "audiolevel_event": true, "audio_active_packets": 100, "audio_level_average": 25}}'
        response = requests.post(
            Cfg.URL_JANUS + "/" + Cfg.dict["session_id"] + "/" + Cfg.dict[
                "plugin_id"], headers=Cfg.HEADERS, data=data,
            verify=True)
        result = json.loads(response.content.decode('ascii'))
        if result["plugindata"]["data"]["videoroom"] == "event":
            print(result["plugindata"]["data"]["error"])
            return False
        else:
            print('Room created    = success ({0} / {1})'.format(Cfg.dict["room"],
                                                                 Cfg.dict["pin"]))
            return Cfg.dict["pin"]

    def join_room(self):
        if 'room' and 'pin' not in Cfg.dict.keys():
            Cfg.dict["room"] = self.select_room_number()
            Cfg.dict["pin"] = self.create_room()

        auth_string = '{{\\"display_name\\":\\"{0}\\",\\"pi_serial\\":\\"{1}\\",\\"room\\":\\"{2}\\",\\"pin\\":\\"{3}\\"}}'.format(
            Cfg.DISPLAY_NAME, Cfg.PI_SERIAL, Cfg.dict["room"], Cfg.dict["pin"])
        data = '{"janus": "message", "transaction": "' + Cfg.dict[
            "transaction_id"] + '", "token": "' + Cfg.AUTH_TOKEN + '", "body": {"request": "join", "ptype": "publisher", "room": ' + \
               Cfg.dict["room"] + ', "pin": "' + Cfg.dict["pin"] + '", "id": ' + \
               Cfg.dict["feed_id"] + ', "display": "' + auth_string + '"}}'
        response = requests.post(
            Cfg.URL_JANUS + "/" + Cfg.dict["session_id"] + "/" + Cfg.dict[
                "plugin_id"], headers=Cfg.HEADERS, data=data,
            verify=True)
        result = json.loads(response.content.decode('ascii'))

        if result["janus"] == "ack":
            print('Join room       = {0} ({1} / {2})'.format(result["janus"], Cfg.dict["room"],
                                                             Cfg.dict["pin"]))
            self.status = "active"
            return True
        else:
            self.counter += 1
            if self.counter < 5:
                print('Join room failed, one more try to join the room')
                self.join_room()
            return False

    def stop(self): # remove your media from the stream
        try:
            data = '{"janus":"message","transaction":"' + Cfg.dict[
                "transaction_id"] + '","token":"' + Cfg.AUTH_TOKEN + '","body":{"request":"unpublish"}}'
            response = requests.post(
                Cfg.URL_JANUS + "/" + Cfg.dict["session_id"] + "/" + Cfg.dict[
                    "plugin_id"], headers=Cfg.HEADERS, data=data,
                verify=True)
            result = json.loads(response.content.decode('ascii'))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            if result["janus"] == 'error':
                print(result["error"]["reason"])
            else:
                print('Unpublish media = {0}'.format(result["janus"]))
            self.destroy_room()
            Cfg.dict.clear()
            self.status = "disabled"

            # set s_streaming to False with output: no streaming sessions active and back to ready for start_processes()
            return False
        except OSError as e:
            print(sys.stderr, "Unpublish media failed:")

    # clean up, so no orphaned rooms will exist
    def destroy_room(self):
        try:
            data = '{"janus": "message", "transaction": "' + Cfg.dict[
                "transaction_id"] + '", "token": "' + Cfg.AUTH_TOKEN + '", "body": {"request": "destroy", "room": ' + \
                   Cfg.dict["room"] + '}}'
            response = requests.post(
                Cfg.URL_JANUS + "/" + Cfg.dict["session_id"] + "/" + Cfg.dict[
                    "plugin_id"], headers=Cfg.HEADERS, data=data,
                verify=True)
            result = json.loads(response.content.decode('ascii'))
            if result["janus"] == 'error':
                print(result["error"]["reason"])
                return False
            else:
                print('Destroy room    = {0} ({1})'.format(result["janus"], Cfg.dict["room"]))
                return True
        except OSError as e:
            print(sys.stderr, "Destroy room failed:", e)
