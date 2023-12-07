import json
import os
from io import BytesIO
from pathlib import Path

import dotenv
import requests
import urllib.request
from PIL import Image

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.nostr_utils import check_and_set_private_key
from utils.output_utils import upload_media_to_hoster
from utils.zap_utils import get_price_per_sat

"""
This File contains a Module to transform an image to a short video clip using Stable Video Diffusion with replicate

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: 
"""


class VideoGenerationReplicateSVD(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_VIDEO
    TASK: str = "image-to-video"
    FIX_COST: float = 120

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "url":
                    return False
        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        url = ""
        frames = 14  # 25
        if frames == 25:
            length = "25_frames_with_svd_xt"
        else:
            length = "14_frames_with_svd"
        sizing_strategy = "maintain_aspect_ratio" #crop_to_16_9, use_image_dimensions
        frames_per_second = 6
        motion_bucket_id = 127  #Increase overall motion in the generated video
        cond_aug = 0.02  # Amount of noise to add to input image

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = tag.as_vec()[1]
        #TODO add params as defined above

        options = {
            "url": url,
            "length": length,
            "sizing_strategy": sizing_strategy,
            "frames_per_second": frames_per_second,
            "motion_bucket_id": motion_bucket_id,
            "cond_aug": cond_aug

        }
        request_form['options'] = json.dumps(options)

        return request_form

    def process(self, request_form):
        try:
            options = DVMTaskInterface.set_options(request_form)
            print(options["url"])
            response = requests.get(options["url"])
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image.save("./outputs/input.jpg")

            import replicate
            output = replicate.run(
                "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                input={"input_image": open("./outputs/input.jpg", "rb"),
                       "video_length": options["length"],
                       "sizing_strategy": options["sizing_strategy"],
                       "frames_per_second": options["frames_per_second"],
                       "motion_bucket_id": options["motion_bucket_id"],
                       "cond_aug": options["cond_aug"]
                       }
            )
            print(output)

            urllib.request.urlretrieve(output, "./outputs/svd.mp4")
            result = upload_media_to_hoster("./outputs/svd.mp4")
            return result

        except Exception as e:
            print("Error in Module")
            raise Exception(e)

# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    profit_in_sats = 10
    cost_in_cent = 4.0
    dvm_config.FIX_COST = int(((cost_in_cent / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip90params = {
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use Replicate to run StableDiffusion XL",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": nip90params
    }


    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return VideoGenerationReplicateSVD(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.UPDATE_PROFILE = False
    admin_config.LUD16 = ""

    dvm = build_example("Stable Video Diffusion", "replicate_svd", admin_config)
    dvm.run()

    keep_alive()
