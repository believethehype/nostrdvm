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
This File contains a module to transform an Image to a short Video Clip on n-server and receive results back. 

Accepted Inputs: An url to an Image
Outputs: An url to a video
, 
"""


class VideoGenerationSVD(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_GENERATE_VIDEO
    TASK: str = "image-to-video"
    FIX_COST: float = 120

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
        request_form["trainerFilePath"] = r'modules\stablevideodiffusion\stablevideodiffusion.trainer'

        url = ""
        frames = 7  # 25
        model = "stabilityai/stable-video-diffusion-img2vid-xt" #,stabilityai/stable-video-diffusion-img2vid


        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = str(tag.as_vec()[1]).split('#')[0]
        # TODO add params as defined above

        io_input = {
            "id": "input_image",
            "type": "input",
            "src": "url:Image",
            "uri": url
        }

        io_output = {
            "id": "output_video",
            "type": "output",
            "src": "request:stream:Video"
        }

        request_form['data'] = json.dumps([io_input, io_output])

        options = {
            "model": model,
            "fps": frames

        }
        request_form['options'] = json.dumps(options)

        return request_form

    async def process(self, request_form):
        try:
            # Call the process route of n-server with our request form.
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
    # A module might have options it can be initialized with, here we set a default model, and the server
    # address it should use. These parameters can be freely defined in the task component
    options = {'server': server_address}

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I create a short video based on an image",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return VideoGenerationSVD(name=name, dvm_config=dvm_config, nip89config=nip89config,
                               admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(VideoGenerationSVD)
