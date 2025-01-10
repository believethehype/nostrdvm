import random
import time
from pathlib import Path
import dotenv
from typing import Dict, List
import requests, json

from nostr_sdk import Kind

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

RELAY_LIST = ["wss://nostr.mom",
              "wss://relay.nostrdvm.com",
              "wss://nostr.oxtr.dev",
              #"wss://relay.nostr.net"
              ]

SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                      #"wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"]




def playground(announce):
    framework = DVMFramework()

    # An Agent that pretends to be a purple Ostrich
    name = "PurpleOstrichIntelligence"
    identifier = "duckduckchat"  # Chose a unique identifier in order to get a lnaddress
    description = "I'm a funny purple Ostrich"
    picture = "https://image.nostr.build/afd3aaf3fba8e71e1a45611e833967c71ae69f1e1c7a271df4370b5d03feee6d.jpg"
    system_prompt = "You are a funny purple ostrich. Reply in a funny way."
    #purple_ostrich = build_dvm(identifier, name, description, picture, system_prompt, announce)
    #framework.add(purple_ostrich)

    # An Agent that pretends to be a Satoshi Nakamoto
    name = "Nakamoto"
    identifier = "satoshichat"  # Chose a unique identifier in order to get a lnaddress
    description = "If you don't believe me or don't get it, I don't have time to try to convince you, sorry."
    picture = "https://image.nostr.build/34583da23265d955bc09550890029d815c44a1351613b7a76e324c8ad6e1e5a7.jpg"
    system_prompt = "Answer as if you were Satoshi Nakamoto, the inventor of Bitcoin."
    satoshi = build_dvm(identifier, name, description, picture, system_prompt, announce)
    framework.add(satoshi)

    # An Agent that pretends to be a Satoshi Nakamoto

    name = "SamurAI"
    identifier = "samuraichat"  # Chose a unique identifier in order to get a lnaddress
    description = "I follow the way of the Samurai"
    picture = "https://image.nostr.build/c370203fe9fefe0f80b8f72e2fdeee926a22fbce7af13d0013b0071756f1f5e7.jpg"
    system_prompt = "Answer as if you were a wise Samrurai."
    #satoshi = build_dvm(identifier, name, description, picture, system_prompt, announce)
    #framework.add(satoshi)






    framework.run()



def build_dvm(identifier, name, description, picture, system_prompt, announce):
        options = {
            "system_prompt": system_prompt,
            "input": "",
        }

        kind = 5050
        admin_config = AdminConfig()
        admin_config.REBROADCAST_NIP89 = announce
        admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
        admin_config.UPDATE_PROFILE = announce

        dvm_config = build_default_config(identifier)
        dvm_config.KIND = Kind(kind)  # Manually set the Kind Number (see data-vending-machines.org)
        dvm_config.SEND_FEEDBACK_EVENTS = False
        dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
        dvm_config.RELAY_LIST = RELAY_LIST
        dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST

        # Add NIP89
        nip89info = {
            "name": name,
            "picture": picture,
            "about": description,
            "supportsEncryption": True,
            "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
            "nip90Params": {
            }
        }

        nip89config = NIP89Config()
        nip89config.KIND = Kind(kind)
        nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
        nip89config.CONTENT = json.dumps(nip89info)

        dvm =  GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                         admin_config=admin_config, options=options)

        async def process(request_form):
            options = dvm.set_options(request_form)
            result = "Kinda rate limited."
            try:
                class ConversationOver(Exception):
                    """Raised when the conversation limit is reached."""
                    pass

                class ChatModel:
                    """Available models for chat."""
                    claude = "claude-3-haiku-20240307"
                    gpt = "gpt-4o-mini"
                    llama = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
                    mistral = "mistralai/Mixtral-8x7B-Instruct-v0.1"

                class ChatInstance:
                    def __init__(self, model: str):
                        self.base = "https://duckduckgo.com/duckchat/v1%s"
                        self.vqd: str = requests.get(
                            self.base % "/status",
                            headers={"x-vqd-accept": "1"},
                            timeout=5
                        ).headers["x-vqd-4"]
                        self.model: str = model
                        self.transcript: List[Dict[str, str]] = []

                    def chat(self, message: str) -> str:
                        """
                        Chat with the chosen model. Takes a message and returns the model's response.
                        """
                        self.transcript.append({"role": "user", "content": message})
                        res = requests.post(
                            self.base % "/chat",
                            headers={"x-vqd-4": self.vqd},
                            timeout=10,
                            json={"model": self.model, "messages": self.transcript},
                        )
                        self.vqd = res.headers["x-vqd-4"]

                        out: str = ""
                        for item in (i.removeprefix("data: ") for i in res.text.split("\n\n")):
                            if item.startswith("[DONE]"):
                                if item.endswith("[LIMIT_CONVERSATION]"):
                                    raise ConversationOver
                                break
                            out += json.loads(item).get("message", "").encode("latin-1").decode()

                        self.transcript.append({"role": "assistant", "content": out})
                        return out

                chat = ChatInstance(ChatModel.llama)
                query = ("{role: system, content: " + options["system_prompt"] + "}" + " {role: user, content:" +
                         options["input"] + "}")


                result = chat.chat(query)
                print(result)

            except Exception as e:
                print(e)
            return result

        dvm.process = process  # overwrite the process function with the above one
        return dvm


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

    playground(announce=True)
