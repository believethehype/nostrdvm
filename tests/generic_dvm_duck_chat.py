import json
from pathlib import Path
from platform import system

import dotenv
from duck_chat import ModelType
from nostr_sdk import Kind

from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag


def playground(announce=False):

    kind = 5050
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "DuckChat"
    identifier = "duckduckchat"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)
    dvm_config.KIND = Kind(kind)  # Manually set the Kind Number (see data-vending-machines.org)
    dvm_config.SEND_FEEDBACK_EVENTS = False

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I'm briding DuckDuckAI'",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.KIND = kind
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {
        "system_prompt": "You are a funny purple ostrich. Reply in a funny way.",
        "input": "",
    }

    dvm = GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)

    async def process(request_form):
        #pip install -U https://github.com/mrgick/duckduckgo-chat-ai/archive/master.zip

        from duck_chat import DuckChat
        options = dvm.set_options(request_form)
        async with DuckChat(model=ModelType.GPT4o) as chat:
            query = ("{role: system, content: " + options["system_prompt"] + "}" +" {role: user, content:" +  options["input"]+ "}")
            result = await chat.ask_question(query)
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

    playground(announce=False)
