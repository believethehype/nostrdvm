import json
from pathlib import Path
import dotenv

from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_sdk import Keys, Kind



def playground(announce=False):
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "Generic DVM"
    identifier = "a_very_generic_dvm"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)
    dvm_config.KIND = Kind(5050)  # Manually set the Kind Number (see data-vending-machines.org)

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I'm just a demo DVM, not doing much.'",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {
        "some_option": "#RunDVM",
    }

    dvm = GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)

    async def process(request_form):
        options = dvm.set_options(request_form)
        result = "The result of the DVM is: "
        result += options["some_option"]
        print(result)
        return result

    dvm.process = process  # overwrite the process function with the above one
    dvm.run(True)

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
    announce = False

    playground(announce=announce)
