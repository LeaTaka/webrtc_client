import json
import os
import socket
import subprocess
import sys
from time import sleep

import requests.packages.urllib3

from src import apa102, utils
from src.cfg import Cfg

requests.packages.urllib3.disable_warnings()
os.chdir(os.path.join('/home/pi/webrtc_client/'))


class Uv4l:
    initial_status = "disabled"
    status = initial_status

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
        Cfg.dict["transaction_id"] = utils.random_generator(40)
        Cfg.dict["feed_id"] = ''.join(filter(str.isdigit, Cfg.dict["transaction_id"]))

        self.stop()  # destroy uv4l processes if any
        self.start_processes()  # fire up uv4l processes
        self.set_token()  # set the secret token for acquiring access to the janus server

        # initiate session & videoroom plugin
        if self.session_start():
            # logging for journalctl
            print('Serial#         = {0}'.format(Cfg.PI_SERIAL))
            print('Transaction_id  = {0}'.format(Cfg.dict["transaction_id"]))
            print('Feed_id         = {0}'.format(Cfg.dict["feed_id"]))
            print('Create session  = Success')
            print('Sessionid       = {0}'.format(Cfg.dict["session_id"]))
            print('Pluginid        = {0}'.format(Cfg.dict["plugin_id"]))
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
        UV4L_SETTINGS = "\
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
            "
        subprocess.call(UV4L_SETTINGS, shell=True)
        sleep(0.5)  # uv4l needs some time to fire up its multiple processes ..

    # prepare uv4l settings with the secret information, which provides access to the janus server
    def set_token(self):
        DATA_UV4L_SET_TOKEN = '{"gateway":{"apisecret":"",' \
                            '"auth_token":"' + Cfg.AUTH_TOKEN + '","root":"/janus","url":"' + Cfg.URL_JANUS + '"},' \
                            '"http_proxy":{"host":"","non_proxy_hosts_regex":"","password":"","port":80,"user":""},' \
                            '"session":{"reconnect_delay_s":3,"reconnect_on_failure":true},"videoroom":{"as_listener":{' \
                            '"audio":false,"data":false,"video":false},"as_publisher":{' \
                            '"adjust_max_bitrate_for_hardware_videocodec":true,"audio":true,"data":true,' \
                            '"max_bitrate_bits":0,"rec_filename":"myrecording","record":false,' \
                            '"use_hardware_videocodec":false,"video":true,"video_format_id":60},"audiocodec":"opus",' \
                            '"fir_freq":0,"is_private":false,"max_bitrate_for_publishers_bits":128000,"max_listeners":3,' \
                            '"max_publishers":6,"permanent":false,"rec_dir":"/usr/share/janus/recordings/","record":false,' \
                            '"room":1234,"room_description":"","room_pin":"","room_secret":"","username":"",' \
                            '"videocodec":"vp8"}} '
        response = requests.put(Cfg.URL_UV4L + "/settings", headers=Cfg.HEADERS, data=DATA_UV4L_SET_TOKEN,
                                verify='cert/server.pem')
        result = json.loads(response.content.decode('ascii'))
        print('Uv4l settings   = {0}'.format(result["response"]["reason"]))

    def session_start(self):
        DATA_UV4L_SESSION_START = '{"what": "create", "plugin": "videoroom", "transaction": "' + Cfg.dict["transaction_id"] + '"}'
        response = requests.post(Cfg.URL_UV4L, headers=Cfg.HEADERS, data=DATA_UV4L_SESSION_START, verify='cert/server.pem')
        result = json.loads(response.content.decode('ascii'))

        if result["what"] == 'error':
            print('Failed. {0}\nTerminating uv4l through shell...'.format(result["error"]["reason"]))
            subprocess.run(["sudo pkill uv4l"], shell=True)
            return False
        else:
            Cfg.dict["session_id"] = result["session_id"]
            Cfg.dict["plugin_id"] = result["plugins"][0]["id"]
            return True

    def subscribe_media(self):
        DATA_UV4L_SUBSCRIBE_MEDIA = '{"what": "publish", "transaction": "' + Cfg.dict["transaction_id"] + '", "body": {"audio": true, "video": false, "data": true, "adjust_max_bitrate_for_hardware_videocodec": true, "max_bitrate_bits": 0, "use_hardware_videocodec": false, "video_format_id": 60, "record": false, "rec_filename": "myrecording"}}'
        response = requests.post(Cfg.URL_UV4L + "/videoroom", headers=Cfg.HEADERS, data=DATA_UV4L_SUBSCRIBE_MEDIA, verify='cert/server.pem')
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
        if Cfg.TEMPERATURE and self.status == "active":
            # open socket only one time during session!!
            while not self.create_socket_connection():
                pass
            apa102.led_set("off", "blue", "off")
            data = '{"temp": "' + str(utils.get_temp()) + '", "id": "' + str(Cfg.dict["feed_id"]) + '"}'
            print(data)
            self.connection.send(str(data).encode())

    def create_socket_connection(self):
        if Cfg.TEMPERATURE:
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
                DATA_UV4L_STOP = '{"what": "destroy", "plugin": "videoroom","transaction": ""}'
                print('Terminating uv4l PID {0} through shell...'.format(self.check_for_processes()))
                response = requests.post(Cfg.URL_UV4L, headers=Cfg.HEADERS, data=DATA_UV4L_STOP,
                                         verify='cert/server.pem')
                result = json.loads(response.content.decode('ascii'))
                if result["what"] == 'error':
                    print(result["error"]["reason"])
                else:
                    print('{0}fully destroyed session'.format(result["what"]))
                subprocess.run(["sudo pkill uv4l"], shell=True)
                self.status = "disabled"
        except OSError as e:
            print(sys.stderr, "Execution failed:", e)
        sleep(0.5)
