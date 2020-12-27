import json
import os
import socket
import subprocess
import sys
from time import sleep
import requests.packages.urllib3
from src import apa102, utils

requests.packages.urllib3.disable_warnings()
os.chdir(os.path.join('/home/pi/webrtc_client/'))


class Uv4l:
    initial_status = "disabled"
    status = initial_status
    cfg = None

    def __init__(self, cfg):
        self.cfg = cfg

    def setup(self):
        i = 1
        while not self.start_streaming() and i <= 5:
            print("Trying to establish a streaming connection ... ")
            if i == 5:
                apa102.led_set("off", "red", "off", 255)
                sleep(0.002)
                apa102.led_set("off", "red", "off")
                # we failed to join the room, so we terminate all uv4l processes
                self.stop()
                break
            sleep(1)
            i += 1
            pass

    # wrapper function that includes all functions required to start streaming
    def start_streaming(self):
        # for each session we create unique id's
        self.stop()  # destroy uv4l processes if any
        self.start_processes()  # fire up uv4l processes
        self.set_token()  # set the secret token for acquiring access to the janus server

        # initiate session & videoroom plugin
        if self.session_start():
            # logging for journalctl
            print('Serial#         = {0}'.format(self.cfg.PI_SERIAL))
            print('Transaction_id  = {0}'.format(self.cfg.TRANSACTION_ID))
            print('Feed_id         = {0}'.format(self.cfg.FEED_ID))
            print('Create session  = Success')
            print('Sessionid       = {0}'.format(self.cfg.SESSION_ID))
            print('Pluginid        = {0}'.format(self.cfg.PLUGIN_ID))
            return True
        else:
            print("there was a big error")
            return False

    # check if a uv4l process is active
    def check_for_processes(self):
        return subprocess.run(["pidof uv4l"], stdout=subprocess.PIPE, universal_newlines=True,
                              shell=True).stdout.strip()

    # start multiple uv4l processes with below configuration
    def start_processes(self):
        subprocess.call(self.cfg.uv4l_settings(), shell=True)
        sleep(0.5)  # uv4l needs some time to fire up its multiple processes ..

    # prepare uv4l settings with the secret information, which provides access to the janus server
    def set_token(self):
        response = requests.put(
            self.cfg.URL_UV4L + "/settings",
            headers=self.cfg.HEADERS,
            data=self.cfg.uv4l_set_token(),
            verify='cert/server.pem')
        result = json.loads(response.content.decode('ascii'))
        print('Uv4l settings   = {0}'.format(result["response"]["reason"]))

    def session_start(self):
        self.cfg.set_transaction_id()
        response = requests.post(
            self.cfg.URL_UV4L,
            headers=self.cfg.HEADERS,
            data=self.cfg.uv4l_session_start(),
            verify='cert/server.pem')
        result = json.loads(response.content.decode('ascii'))
        # result = self.uv4lResponse(self.cfg.uv4l_session_start(), self.cfg)

        if result["what"] == 'error':
            print('Failed. {0}\nTerminating uv4l through shell...'.format(result["error"]["reason"]))
            subprocess.run(["sudo pkill uv4l"], shell=True)
            return False
        else:
            self.cfg.SESSION_ID = result["session_id"]
            self.cfg.PLUGIN_ID = result["plugins"][0]["id"]
            return True

    def subscribe_media(self):
        response = requests.post(
            self.cfg.URL_UV4L + "/videoroom",
            headers=self.cfg.HEADERS,
            data=self.cfg.uv4l_subscribe_media(),
            verify='cert/server.pem')
        result = json.loads(response.content.decode('ascii'))
        print('Subscribe media = {0}'.format(result["what"]))
        if result["what"] == 'ack':
            # show that we joined and subscribed our media, we are live streaming !
            apa102.led_fade_in("green", "green", "green")
            apa102.led_set("red", "red", "red", 255)
            sleep(0.05)
            apa102.led_fade_out("green", "green", "green")
            apa102.led_set("off", "green", "off")
            self.status = "active"
            # send to socket if facilitated
            self.send_to_socket()
            return True
        else:
            print("Error in subscribe_media_init (missing apitoken/secret?)")
            apa102.led_set("blue", "magenta", "blue")
            return False

    def send_to_socket(self):
        if self.cfg.TEMPERATURE and self.status == "active":
            # open socket only one time during session!!
            while not self.create_socket_connection():
                pass
            apa102.led_set("off", "blue", "off")
            data = '{"temp": "' + str(utils.get_temp()) + '", "id": "' + str(self.cfg.FEED_ID) + '"}'
            print(data)
            self.connection.send(str(data).encode())

    def create_socket_connection(self):
        if self.cfg.TEMPERATURE:
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

    def stop(self):
        try:
            if self.check_for_processes():
                print('Terminating uv4l PID {0} through shell...'.format(self.check_for_processes()))
                response = requests.post(
                    self.cfg.URL_UV4L,
                    headers=self.cfg.HEADERS,
                    data=self.cfg.uv4l_stop(),
                    verify='cert/server.pem')
                result = json.loads(response.content.decode('ascii'))
                if result["what"] == 'error':
                    print(result["error"]["reason"])
                else:
                    print('{0}fully destroyed session'.format(result["what"]))
                subprocess.run(["sudo pkill uv4l"], shell=True)
                self.status = "disabled"
                apa102.led_set("off", "off", "off")
        except OSError as e:
            print(sys.stderr, "Execution failed:", e)
        sleep(0.5)
