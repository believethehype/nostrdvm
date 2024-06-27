import json
import os
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


class VideoGenerationReplicateSVD(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_GENERATE_VIDEO
    TASK: str = "image-to-video"
    FIX_COST: float = 120
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("replicate", "replicate")]

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "url":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        url = ""
        frames = 14  # 25
        if frames == 25:
            length = "25_frames_with_svd_xt"
        else:
            length = "14_frames_with_svd"
        sizing_strategy = "maintain_aspect_ratio"  # crop_to_16_9, use_image_dimensions
        frames_per_second = 6
        motion_bucket_id = 127  # Increase overall motion in the generated video
        cond_aug = 0.02  # Amount of noise to add to input image

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = str(tag.as_vec()[1]).split('#')[0]
        # TODO add params as defined above

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

    async def process(self, request_form):
        try:
            options = self.set_options(request_form)
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
            result = await upload_media_to_hoster("./outputs/svd.mp4")
            return result

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
        "about": "I use Replicate to run StableDiffusion XL",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return VideoGenerationReplicateSVD(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                       admin_config=admin_config)


if __name__ == '__main__':
    process_venv(VideoGenerationReplicateSVD)
