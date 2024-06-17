import asyncio
import json
import os
import time
from io import BytesIO
import requests
import urllib.request
from PIL import Image
from nostr_sdk import Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import upload_media_to_hoster
from nostr_dvm.utils.zap_utils import get_price_per_sat

"""
This File contains a Module to transform an image to a short video clip using Stable Video Diffusion with replicate

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: 
"""


class AudioGenerationSonoAI(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_GENERATE_MUSIC
    TASK: str = "prompt-to-music"
    FIX_COST: float = 120

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        self.base_url = 'http://localhost:3000'

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}

        prompt = "A popular heavy metal song about a purple Ostrich, Nostr, sung by a deep-voiced male singer, slowly and melodiously. The lyrics depict hope for a better future."
        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = str(tag.as_vec()[1])
        # TODO add params as defined above

        options = {
            "prompt": prompt,
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def custom_generate_audio(self, payload):
        url = f"{self.base_url}/api/custom_generate"
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        return response.json()

    def extend_audio(self, payload):
        url = f"{self, self.base_url}/api/extend_audio"
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        return response.json()

    def generate_audio_by_prompt(self, payload):
        url = f"{self.base_url}/api/generate"
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        return response.json()

    def get_audio_information(self, audio_ids):
        url = f"{self.base_url}/api/get?ids={audio_ids}"
        response = requests.get(url)
        return response.json()

    def get_quota_information(self):
        url = f"{self.base_url}/api/get_limit"
        response = requests.get(url)
        return response.json()

    def get_clip(self, clip_id):
        url = f"{self.base_url}/api/clip?id={clip_id}"
        response = requests.get(url)
        return response.json()

    def generate_whole_song(self, clip_id):
        payload = {"clip_id": clip_id}
        url = f"{self.base_url}/api/concat"
        response = requests.post(url, json=payload)
        return response.json()

    async def process(self, request_form):
        try:
            options = self.set_options(request_form)
            has_quota = False
            quota_info = self.get_quota_information()

            if int(quota_info['credits_left']) >= 20:
                has_quota = True
            else:
                print("No quota left, exiting.")

            if has_quota:

                data = self.generate_audio_by_prompt({
                    "prompt": options["prompt"],
                    "make_instrumental": False,
                    "wait_audio": False
                })
                if len(data) == 0:
                    print("Couldn't create song")
                    pass

                ids = f"{data[0]['id']},{data[1]['id']}"
                print(f"ids: {ids}")

                for _ in range(60):
                    data = self.get_audio_information(ids)
                    if data[0]["status"] == 'streaming':
                        print(f"{data[0]['id']} ==> {data[0]['video_url']}")
                        print(f"{data[1]['id']} ==> {data[1]['video_url']}")
                        break
                    # sleep 5s
                    await asyncio.sleep(5.0)

                response1 = self.get_clip(data[0]['id'])
                print(response1['video_url'])
                print(response1['prompt'])

                response2 = self.get_clip(data[1]['id'])
                print(response2['video_url'])
                #print(response2['prompt']) #same as 1

                return response1['video_url'] + "\n" + response2['video_url'] + "\n" + response1['prompt']

        except Exception as e:
            print("Error in Module")
            raise Exception(e)


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    profit_in_sats = 10
    cost_in_cent = 4.0
    dvm_config.FIX_COST = int(((cost_in_cent / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I create songs based on prompts with suno.ai",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return AudioGenerationSonoAI(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                 admin_config=admin_config)


if __name__ == '__main__':
    process_venv(AudioGenerationSonoAI)
