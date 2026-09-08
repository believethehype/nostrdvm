import os
from pathlib import Path

import dotenv


def get_env_path():
    return Path(__file__).resolve().parents[2] / ".env"


def load_env():
    return dotenv.load_dotenv(get_env_path(), override=False)


def set_env_key(key, value):
    env_path = get_env_path()
    if env_path.is_file():
        dotenv.set_key(env_path, key, value)
    os.environ[key] = value
