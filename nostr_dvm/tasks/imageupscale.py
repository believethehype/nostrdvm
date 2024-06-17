import json
import os
from multiprocessing.pool import ThreadPool

from nostr_sdk import Kind

from nostr_dvm.backends.nova_server.utils import check_server_status, send_request_to_server
from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.definitions import EventDefinitions

"""
This File contains a Module to upscale an image from an url by factor 2-4 

Accepted Inputs: link to image (url)
Outputs: An url to an Image
Params: -upscale        2,3,4
"""


class ImageUpscale(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "image-to-image"
    FIX_COST: float = 20

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        hasurl = False
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    hasurl = True

        if not hasurl:
            return False

        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        request_form["trainerFilePath"] = r'modules\image_upscale\image_upscale_realesrgan.trainer'
        url = ""
        out_scale = 4

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "upscale":
                    out_scale = int(tag.as_vec()[2])

        io_input_image = {
            "id": "input_image",
            "type": "input",
            "src": "url:image",
            "uri": url
        }

        io_output = {
            "id": "output_image",
            "type": "output",
            "src": "request:image"
        }

        request_form['data'] = json.dumps([io_input_image, io_output])

        options = {"model": "RealESRGAN_x4plus",
                   "outscale": out_scale,
                   "denoise_strength": 0.5,
                   "tile": 0,
                   "tile_pad": 10,
                   "pre_pad": 0,
                   "compute_type": "fp32",
                   "face_enhance": False}

        request_form['options'] = json.dumps(options)

        return request_form

    async def process(self, request_form):
        try:
            # Call the process route of NOVA-Server with our request form.
            response = send_request_to_server(request_form, self.options['server'])
            if bool(json.loads(response)['success']):
                print("Job " + request_form['jobID'] + " sent to server")

            pool = ThreadPool(processes=1)
            thread = pool.apply_async(check_server_status, (request_form['jobID'], self.options['server']))
            print("Wait for results of server...")
            result = thread.get()
            return result

        except Exception as e:
            raise Exception(e)


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, server_address):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # A module might have options it can be initialized with, here we set a default model, lora and the server
    options = {'server': server_address}

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/229c14e440895da30de77b3ca145d66d4b04efb4027ba3c44ca147eecde891f1.jpg",
        "about": "I upscale an image using realESRGan up to factor 4 (default is factor 4)",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "upscale": {
                "required": False,
                "values": ["2", "3", "4"]
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return ImageUpscale(name=name, dvm_config=dvm_config, nip89config=nip89config,
                        admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(ImageUpscale)
