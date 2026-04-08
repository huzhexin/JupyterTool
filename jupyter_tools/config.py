import configparser
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")

_cfg = configparser.ConfigParser()
_cfg.read(_CONFIG_PATH)

BASE_URL = f"http://{_cfg['jupyter']['host']}:{_cfg['jupyter']['port']}"
TOKEN = _cfg["jupyter"]["token"]
HEADERS = {"Authorization": f"token {TOKEN}"}
WS_URL = BASE_URL.replace("http", "ws")
