import json
from pathlib import Path
import dotenv
from nostr_dvm.tasks import texttospeech
from nostr_dvm.tasks.texttospeech import TextToSpeech
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag

if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')
    name = "TTS Guy Swann"
    identifier = "ttsguy"
    admin_config_tts = AdminConfig()
    admin_config_tts.UPDATE_PROFILE = True
    admin_config_tts.REBROADCAST_NIP65_RELAY_LIST = True
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = True
    dvm_config.FIX_COST = 0
    dvm_config.PER_UNIT_COST = 0
    relays = dvm_config.RELAY_LIST
    relays.append("wss://relay.damus.io")
    relays.append("wss://relay.primal.net")
    dvm_config.RELAY_LIST = relays

    admin_config_tts.LUD16 = dvm_config.LN_ADDRESS
    # use an alternative local wav file you want to use for cloning
    options = {'input_file': ""}
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I Generate Speech from Text",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "language": {
                "required": False,
                "values": []
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    tts = TextToSpeech(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config_tts,
                       options=options)
    tts.run()
