import json
import os
from pathlib import Path

import dotenv


from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag

"""
This File contains a Module to generate Text, based on a prompt using a LLM (local or API) (Ollama, custom model, chatgpt)

Accepted Inputs: Prompt (text)
Outputs: Generated text
"""


class TextGenerationOLLAMA(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_TEXT
    TASK: str = "text-to-text"
    FIX_COST: float = 0
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("litellm", "litellm==1.12.3")]

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        super().__init__(name, dvm_config, nip89config, admin_config, options)


    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False

        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        prompt = ""
        if self.options.get("default_model") and self.options.get("default_model") != "":
            model = self.options['default_model']
        else:
            model = "gpt-3.5-turbo" #"gpt-4-1106-preview" # This will call chatgpt and requires an OpenAI API Key set in .env
        if self.options.get("server") and self.options.get("server") != "":
            server = self.options['server']
        else:
            server = "http://localhost:11434" #default ollama server. This will only be used for ollama models.

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]

        options = {
            "prompt": prompt,
            "model": model,
            "server": server
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def process(self, request_form):
        from litellm import completion

        options = DVMTaskInterface.set_options(request_form)

        try:
            if options["model"].startswith("ollama"):
                response = completion(
                    model=options["model"],
                    messages=[{"content": options["prompt"], "role": "user"}],
                    api_base=options["server"]
                )
                print(response.choices[0].message.content)
                return response.choices[0].message.content
            else:
                response = completion(
                    model=options["model"],
                    messages=[{"content": options["prompt"], "role": "user"}],
                )
                print(response.choices[0].message.content)
                return response.choices[0].message.content

        except Exception as e:
            print("Error in Module: " + str(e))
            raise Exception(e)


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    options = {'default_model': "ollama/llama2-uncensored", 'server': "http://localhost:11434"}

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use a LLM connected via OLLAMA",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "size": {
                "required": False,
                "values": ["1024:1024", "1024x1792", "1792x1024"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return TextGenerationOLLAMA(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config, options=options)


def process_venv():
    args = DVMTaskInterface.process_args()
    dvm_config = build_default_config(args.identifier)
    dvm = TextGenerationOLLAMA(name="", dvm_config=dvm_config, nip89config=NIP89Config(), admin_config=None)
    result = dvm.process(json.loads(args.request))
    DVMTaskInterface.write_output(result, args.output)


#if __name__ == '__main__':
#    env_path = Path('.env')
#    if env_path.is_file():
#        print(f'loading environment from {env_path.resolve()}')
#        dotenv.load_dotenv(env_path, verbose=True, override=True)
#    else:
#        raise FileNotFoundError(f'.env file not found at {env_path} ')
#
#    admin_config = AdminConfig()
#    admin_config.REBROADCAST_NIP89 = False
#    admin_config.UPDATE_PROFILE = False
#
#    dvm = build_example("LLM", "llmlite", admin_config)
#    dvm.run()

#    keep_alive()
