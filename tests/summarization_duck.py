import json
from pathlib import Path

import dotenv
from nostr_dvm.tasks.summarization_duckduck_ai import SummarizationDuckDuck
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag


def playground(announce=False):
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "Summarizer Duck"
    identifier = "summarizer_duck"
    dvm_config = build_default_config(identifier)
    dvm_config.SEND_FEEDBACK_EVENTS = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I summarize Text",
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)


    dvm = SummarizationDuckDuck(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                 admin_config=admin_config)
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

    playground(announce=False)
