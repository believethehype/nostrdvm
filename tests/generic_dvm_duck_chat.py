import json
from pathlib import Path

import dotenv
from duck_chat import ModelType
from nostr_sdk import Kind

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

RELAY_LIST = ["wss://nostr.mom",
              #"wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              #"wss://relay.nostr.net"
              ]

SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                      #"wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"]



def playground(announce=False):

    framework = DVMFramework()
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
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST


    # Add NIP89
    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I'm briding DuckDuckAI'",
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.KIND = Kind(kind)
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
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
        result = "No worky"
        try:
            """
            Simple Python client for ddg.gg/chat
            """

            from typing import Dict, List
            import requests, json

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
                        timeout=5,
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


            chat = ChatInstance(ChatModel.gpt)
            query = ("{role: system, content: " + options["system_prompt"] + "}" + " {role: user, content:" +
                     options["input"] + "}")

            result = chat.chat(query)
            print(result)

        except Exception as e:
            print(e)
        return result

    dvm.process = process  # overwrite the process function with the above one
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

    playground(announce=False)
