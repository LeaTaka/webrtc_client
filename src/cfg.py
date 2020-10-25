import hashlib
import string
import subprocess
import random


class Cfg:
    # all uv4l and Janus settings created during setup of a stream
    dict = {}
    # A random number is used for generating a transaction_id and feed_id
    DISPLAY_NAME = "LeasCrib"
    URL_UV4L = "https://localhost:8889/api/janus/client"
    URL_JANUS = "https://www.jasconcept.com:8089/janus"
    HEADERS = {'Content-type': 'application/json'}

    TRANSACTION_ID = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(40))
    FEED_ID = ''.join(filter(str.isdigit, TRANSACTION_ID))
    SESSION_ID = None
    PLUGIN_ID = None
    TEMPERATURE = False
    PI_SERIAL = subprocess.run(
        ["printf $(vcgencmd otp_dump | grep '28:')"],
        check=True, stdout=subprocess.PIPE,
        universal_newlines=True,
        shell=True).stdout.strip()
    AUTH_TOKEN = hashlib.sha256(PI_SERIAL.encode()).hexdigest()

    room = None
    pin = None

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # UV4L SETTING FROM HERE                                                                                #
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def uv4l_settings(self):
        return "uv4l --auto-video_nr --driver dummy --frame-buffers=2 \
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
                --server-option '--janus-gateway-url=https://www.jasconcept.com:8089'"

    def uv4l_set_token(self):
        return '{"gateway":{"apisecret":"",' \
               '"auth_token":"' + self.AUTH_TOKEN + '","root":"/janus","url":"' + self.URL_JANUS + '"},' \
               '"http_proxy":{"host":"","non_proxy_hosts_regex":"","password":"","port":80,"user":""},' \
               '"session":{"reconnect_delay_s":3,"reconnect_on_failure":true},"videoroom":{"as_listener":{' \
               '"audio":false,"data":false,"video":false},"as_publisher":{' \
               '"adjust_max_bitrate_for_hardware_videocodec":true,"audio":true,"data":true,' \
               '"max_bitrate_bits":0,"rec_filename":"myrecording","record":false,' \
               '"use_hardware_videocodec":false,"video":true,"video_format_id":60},"audiocodec":"opus",' \
               '"fir_freq":0,"is_private":false,"max_bitrate_for_publishers_bits":128000,"max_listeners":3,' \
               '"max_publishers":6,"permanent":false,"rec_dir":"/usr/share/janus/recordings/","record":false,' \
               '"room":1234,"room_description":"","room_pin":"","room_secret":"","username":"",' \
               '"videocodec":"vp8"}}'

    def uv4l_subscribe_media(self):
        return '{"what": "publish", ' \
               '"transaction": "' + self.TRANSACTION_ID + '", ' \
               '"body": {"audio": true, ' \
               '"video": false, ' \
               '"data": true, ' \
               '"adjust_max_bitrate_for_hardware_videocodec": true, ' \
               '"max_bitrate_bits": 0, ' \
               '"use_hardware_videocodec": false, ' \
               '"video_format_id": 60, ' \
               '"record": false, ' \
               '"rec_filename": "myrecording"}}'

    def uv4l_session_start(self):
        return '{"what": "create", "plugin": "videoroom", "transaction": "' + self.TRANSACTION_ID + '"}'

    def uv4l_stop(self):
        return '{"what": "destroy", "plugin": "videoroom","transaction": ""}'

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # JANUS SETTING FROM HERE                                                                               #
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def janus_select_room_number(self):
        return '{"janus": "message", ' \
               '"transaction": "' + self.TRANSACTION_ID + '", ' \
               '"token": "' + self.AUTH_TOKEN + '", ' \
               '"body": {"request": "list"}} '

    def janus_create_room(self):
        return '{"janus": "message", ' \
               '"transaction": "' + self.TRANSACTION_ID + '", ' \
               '"token": "' + self.AUTH_TOKEN + '", ' \
               '"body": {"request": "create", ' \
               '"audiocodec": "opus", ' \
               '"bitrate": 128000, ' \
               '"description": "Pretty room", ' \
               '"fir_freq": 10, ' \
               '"notify_joining": false, ' \
               '"record": false, ' \
               '"require_pvtid": false, ' \
               '"room": ' + self.room + ', ' \
               '"pin": "' + self.pin + '", ' \
               '"videocodec": "h264", ' \
               '"audiolevel_event": true, ' \
               '"audio_active_packets": 100, ' \
               '"audio_level_average": 25}}'

    def janus_join_room(self):
        AUTH_STRING = '{{\\"display_name\\":\\"{0}\\",\\"pi_serial\\":\\"{1}\\",\\"room\\":\\"{2}\\",\\"pin\\":\\"{3}\\"}}'.format(
            # special formatting for serverside requirements
            self.DISPLAY_NAME,
            self.PI_SERIAL,
            self.room,
            self.pin)
        return '{"janus": "message", ' \
               '"transaction": "' + self.TRANSACTION_ID + '", ' \
               '"token": "' + self.AUTH_TOKEN + '", ' \
               '"body": {"request": "join", ' \
               '"ptype": "publisher", ' \
               '"room": ' + self.room + ', ' \
               '"pin": "' + self.pin + '", ' \
               '"id": ' + self.FEED_ID + ', ' \
               '"display": "' + AUTH_STRING + '"}}'

    def janus_stop(self):
        return '{"janus":"message", ' \
               '"transaction":"' + self.TRANSACTION_ID + '", ' \
               '"token":"' + self.AUTH_TOKEN + '", ' \
               '"body":{"request":"unpublish"}}'

    def janus_destroy_room(self):
        return '{"janus": "message", ' \
               '"transaction": "' + self.TRANSACTION_ID + '", ' \
               '"token": "' + self.AUTH_TOKEN + '", ' \
               '"body": {"request": "destroy", ' \
               '"room": ' + self.room + '}}'
