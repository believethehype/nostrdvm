import json
import os
from pathlib import Path
import dotenv

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_sdk import Kind


def main(announce=False):
    framework = DVMFramework()

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "Generic D V M"
    identifier = "genericdvm"
    dvm_config = build_default_config(identifier)
    dvm_config.KIND = Kind(5000)
    dvm_config.FIX_COST = 0.0

    # Add NIP89
    nip89info = {
    "name": "Generic D V M",
    "picture": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
    "about": "test",
    "supportsEncryption": true,
    "acceptsNutZaps": true,
    "nip90Params": {}
}

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {}

    dvm = GenericDVM(
        name=name, 
        dvm_config=dvm_config, 
        nip89config=nip89config,
        admin_config=admin_config, 
        options=options
    )

    framework.add(dvm)
    framework.run()


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
    
    announce = os.getenv("ANNOUNCE", "False").lower() == "true"
    main(announce=announce)
