import asyncio
import os
from pathlib import Path

import dotenv
from nostr_sdk import Keys, PublicKey

from nostr_dvm.utils import dvmconfig
from nostr_dvm.utils.nwc_tools import nwc_zap
from nostr_dvm.utils.zap_utils import zaprequest


async def playground():

    connectionstr = os.getenv("TEST_NWC")
    keys = Keys.parse(os.getenv("TEST_USER"))
    bolt11 = zaprequest("bot@nostrdvm.com", 5, "test", None, PublicKey.parse("npub1cc79kn3phxc7c6mn45zynf4gtz0khkz59j4anew7dtj8fv50aqrqlth2hf"), keys, dvmconfig.DVMConfig.RELAY_LIST, zaptype="private")
    print(bolt11)
    result = await nwc_zap(connectionstr, bolt11, keys, externalrelay=None)
    print(result)


if __name__ == '__main__':
    env_path = Path('.env')
    if not env_path.is_file():
        with open('.env', 'w') as f:
            print("Writing new .env file")
            f.write('')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')
    asyncio.run(playground())