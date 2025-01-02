import asyncio
import os
from pathlib import Path

import dotenv
from nostr_sdk import Keys
from nostr_dvm.utils.blossom_utils import upload_blossom
from nostr_dvm.utils.output_utils import upload_media_to_hoster

if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    pkey = os.getenv("DVM_PRIVATE_KEY_BOT")


    #asyncio.run(upload_media_to_hoster("tests/image.png", pkey, True))
    asyncio.run(upload_blossom("tests/cat4.png",  pkey, "https://blossom.primal.net"))

