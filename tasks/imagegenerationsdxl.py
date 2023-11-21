import os
from multiprocessing.pool import ThreadPool
from threading import Thread

from backends.nova_server import check_nova_server_status, send_request_to_nova_server
from dvm import DVM
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig

"""
This File contains a Module to transform Text input on NOVA-Server and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
"""


class ImageGenerationSDXL(DVMTaskInterface):
    NAME: str = ""
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    COST: int = 50
    PK: str

    def __init__(self, name, dvm_config: DVMConfig, admin_config: AdminConfig = None, default_model=None, default_lora=None):
        self.NAME = name
        dvm_config.SUPPORTED_TASKS = [self]
        dvm_config.DB = "db/" + self.NAME + ".db"
        self.PK = dvm_config.PRIVATE_KEY
        self.default_model = default_model
        self.default_lora = default_lora

        dvm = DVM
        nostr_dvm_thread = Thread(target=dvm, args=[dvm_config, admin_config])
        nostr_dvm_thread.start()


    def is_input_supported(self, input_type, input_content):
        if input_type != "text":
            return False
        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_"+ self.NAME.replace(" ", "")}
        request_form["trainerFilePath"] = 'modules\\stablediffusionxl\\stablediffusionxl.trainer'

        prompt = ""
        negative_prompt = ""
        if self.default_model is None:
            model = "stabilityai/stable-diffusion-xl-base-1.0"
        else:
            model = self.default_model

        # models: juggernautXL, dynavisionXL, colossusProjectXL, newrealityXL, unstable
        ratio_width = "1"
        ratio_height = "1"
        width = ""
        height = ""
        if self.default_lora == None:
            lora = ""
        else:
            lora = self.default_lora
        lora_weight = ""
        strength = ""
        guidance_scale = ""
        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print(tag.as_vec()[2])
                if tag.as_vec()[1] == "negative_prompt":
                    negative_prompt = tag.as_vec()[2]
                elif tag.as_vec()[1] == "lora":
                    lora = tag.as_vec()[2]
                elif tag.as_vec()[1] == "lora_weight":
                    lora_weight = tag.as_vec()[2]
                elif tag.as_vec()[1] == "strength":
                    strength = tag.as_vec()[2]
                elif tag.as_vec()[1] == "guidance_scale":
                    guidance_scale = tag.as_vec()[2]
                elif tag.as_vec()[1] == "ratio":
                    if len(tag.as_vec()) > 3:
                        ratio_width = (tag.as_vec()[2])
                        ratio_height = (tag.as_vec()[3])
                    elif len(tag.as_vec()) == 3:
                        split = tag.as_vec()[2].split(":")
                        ratio_width = split[0]
                        ratio_height = split[1]
                    #if size is set it will overwrite ratio.
                elif tag.as_vec()[1] == "size":

                    if len(tag.as_vec()) > 3:
                         width = (tag.as_vec()[2])
                         height = (tag.as_vec()[3])
                    elif len(tag.as_vec()) == 3:
                        split = tag.as_vec()[2].split("x")
                        if len(split) > 1:
                            width = split[0]
                            height = split[1]
                elif tag.as_vec()[1] == "model":
                    model = tag.as_vec()[2]

        prompt = prompt.replace(";", ",")
        request_form['data'] = '[{"id":"input_prompt","type":"input","src":"request:text","data":"' + prompt + '","active":"True"},{"id":"negative_prompt","type":"input","src":"request:text","data":"' + negative_prompt + '","active":"True"},{"id":"output_image","type":"output","src":"request:image","active":"True"}]'
        request_form['options'] = ('[{"model":" + ' + model
                                   + '","ratio":"' + str(ratio_width) + ':' + str(ratio_height)
                                   + '","width":"' + str(width) + ':' + str(height)
                                   + '","strength":"' + str(strength)
                                   + '","guidance_scale":"' + str(guidance_scale)
                                   + '","lora":"' + str(lora)
                                   + '","lora_weight":"' + str(lora_weight)
                                   + '"}]')


        request_form["optStr"] = ('model=' + model + ';ratio=' + str(ratio_width) + '-' + str(ratio_height) + ';size=' +
                                  str(width) + '-' + str(height) + ';strength=' + str(strength) + ';guidance_scale=' +
                                  str(guidance_scale) + ';lora=' + lora + ';lora_weight=' + lora_weight)

        return request_form

    def process(self, request_form):
        try:
            # Call the process route of NOVA-Server with our request form.
            success = send_request_to_nova_server(request_form, os.environ["NOVA_SERVER"])
            print(success)

            pool = ThreadPool(processes=1)
            thread = pool.apply_async(check_nova_server_status, (request_form['jobID'], os.environ["NOVA_SERVER"]))
            print("Wait for results of NOVA-Server...")
            result = thread.get()
            return str(result)

        except Exception as e:
            raise Exception(e)
