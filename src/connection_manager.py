from cfg import Cfg
from src import apa102
from src.uv4l import Uv4l
from src.janus import Janus


class ConnectionManager:
    recover = None

    dummy_uv4l = Uv4l()
    dummy_janus = Janus()

    def ensure_status(self, status, internet):

        print(f"internet: {internet}, uv4l: {self.dummy_uv4l.status}, janus: {self.dummy_janus.status}")

        if self.recover and internet:
            print(f"recovering with settings: {str(Cfg.dict)}")
            self.dummy_uv4l.setup()
            self.dummy_janus.join_room()
            self.dummy_uv4l.subscribe_media()
            self.recover = False

        elif status == "active" and internet:
            if self.dummy_uv4l.status == "disabled":
                self.dummy_uv4l.setup()
                self.dummy_janus.join_room()
                self.dummy_uv4l.subscribe_media()

        elif status == "active" and not internet:
            print("waiting for internet")
            self.recover = True
            apa102.led_set("blue", "blue", "blue")

        else:
            if self.dummy_janus.status == "active":
                self.dummy_janus.stop()
            if self.dummy_uv4l.status == "active":
                self.dummy_uv4l.stop()
