import json
import os
import sys
import requests
from src import utils
from src.cfg import Cfg

os.chdir(os.path.join('/home/pi/webrtc_client/'))

class Janus:
    initial_status = "disabled"
    status = initial_status
    counter = 0
    cfg = None

    def __init__(self, cfg):
        self.cfg = cfg

    # choose a random room number and check if it exists, continue until a unique number is found
    def select_room_number(self):
        response = requests.post(
            Cfg.URL_JANUS + "/" + self.cfg.SESSION_ID + "/" + self.cfg.PLUGIN_ID,
            headers=Cfg.HEADERS,
            data=self.cfg.janus_select_room_number(),
            verify=True)
        result = json.loads(response.content.decode('ascii'))
        rooms = [(list['room']) for list in result["plugindata"]["data"]["list"]]
        print('Number of rooms = {}'.format(len(rooms)))
        # print('Active rooms    = {0}'.format(str(rooms)[1:-1]))
        self.cfg.room = (self.cfg.FEED_ID.strip("0") * 5)[:5]
        while True:
            if self.cfg.room in set(rooms):
                self.cfg.room = int(utils.random_generator(5, "1234567890").strip("0"))
                continue
            else:
                return str(self.cfg.room)

    def create_room(self):
        self.cfg.pin = (self.cfg.FEED_ID.strip("0") * 4)[-4:]
        response = requests.post(
            Cfg.URL_JANUS + "/" + self.cfg.SESSION_ID + "/" + self.cfg.PLUGIN_ID,
             headers=Cfg.HEADERS,
             data=self.cfg.janus_create_room(),
             verify=True)
        result = json.loads(response.content.decode('ascii'))
        if result["plugindata"]["data"]["videoroom"] == "event":
            print(result["plugindata"]["data"]["error"])
            return False
        else:
            print('Room created    = success ({0} / {1})'.format(self.cfg.room,
                                                                 self.cfg.pin))
            return self.cfg.pin

    def join_room(self):
        if not self.cfg.room and not self.cfg.pin:
            self.cfg.room = self.select_room_number()
            self.cfg.pin = self.create_room()
        response = requests.post(
            Cfg.URL_JANUS + "/" + self.cfg.SESSION_ID + "/" + self.cfg.PLUGIN_ID,
            headers=Cfg.HEADERS,
            data=self.cfg.janus_join_room(),
            verify=True)
        result = json.loads(response.content.decode('ascii'))

        if result["janus"] == "ack":
            print('Join room       = {0} ({1} / {2})'.format(
                result["janus"], self.cfg.room, self.cfg.pin))
            self.status = "active"
            return True
        else:
            self.counter += 1
            if self.counter < 5:
                print('Join room failed, one more try to join the room')
                self.join_room()
            return False

    def stop(self):  # remove your media from the stream
        try:
            response = requests.post(
                Cfg.URL_JANUS + "/" + self.cfg.SESSION_ID + "/" + self.cfg.PLUGIN_ID,
                headers=Cfg.HEADERS,
                data=self.cfg.janus_stop(),
                verify=True)
            result = json.loads(response.content.decode('ascii'))
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            if result["janus"] == 'error':
                print(result["error"]["reason"])
            else:
                print('Unpublish media = {0}'.format(result["janus"]))
            self.destroy_room()
            self.cfg.room = None
            self.cfg.pin = None
            self.status = "disabled"

            # set s_streaming to False with output: no streaming sessions active and back to ready for start_processes()
            return False
        except OSError as e:
            print(sys.stderr, "Unpublish media failed:", e)

    # clean up, so no orphaned rooms will exist
    def destroy_room(self):
        try:
            response = requests.post(
                Cfg.URL_JANUS + "/" + self.cfg.SESSION_ID + "/" + self.cfg.PLUGIN_ID,
                headers=Cfg.HEADERS, data=self.cfg.janus_destroy_room(), verify=True)
            result = json.loads(response.content.decode('ascii'))
            if result["janus"] == 'error':
                print(result["error"]["reason"])
                return False
            else:
                print('Destroy room    = {0} ({1})'.format(result["janus"], self.cfg.room))
                return True
        except OSError as e:
            print(sys.stderr, "Destroy room failed:", e)






