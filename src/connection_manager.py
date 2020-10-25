from src import apa102
from src.uv4l import Uv4l
from src.janus import Janus
from src.cfg import Cfg


class ConnectionManager:
    recover = None

    uv4l = Uv4l()
    janus = Janus()

    def ensure_status(self, status, internet):

        # print(f"internet: {internet}, uv4l: {self.dummy_uv4l.status}, janus: {self.dummy_janus.status}")

        if self.recover and internet:
            print(f"recovering with room: {str(self.uv4l.cfg.room)}")
            self.uv4l.setup()
            self.janus.join_room()
            self.uv4l.subscribe_media()
            self.recover = False

        elif status == "active" and internet:
            if self.uv4l.status == "disabled":
                self.uv4l.setup()
                self.janus.join_room()
                self.uv4l.subscribe_media()

        elif status == "active" and not internet:
            print("waiting for internet")
            self.recover = True
            apa102.led_set("blue", "blue", "blue")

        else:
            if self.janus.status == "active":
                self.janus.stop()
            if self.uv4l.status == "active":
                self.uv4l.stop()
