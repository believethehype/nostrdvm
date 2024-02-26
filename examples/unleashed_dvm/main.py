import json
from pathlib import Path
import dotenv

from nostr_dvm.tasks.textgeneration_unleashed_chat import TextGenerationUnleashedChat
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag


def main():
    identifier = "unleashed"
    name = "Unleashed Chat"
    dvm_config = build_default_config(identifier)
    dvm_config.SEND_FEEDBACK_EVENTS = False
    dvm_config.USE_OWN_VENV = False
    dvm_config.FIX_COST = 0
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = False


    nip89info = {
        "name": name,
        "image": "https://unleashed.chat/_app/immutable/assets/hero.pehsu4x_.jpeg",
        "about": "I generate Text with Unleashed.chat",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)



    unleashed =  TextGenerationUnleashedChat(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)
    unleashed.run()




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
    main()
