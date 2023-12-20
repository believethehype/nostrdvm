"""StableDiffusionXL Module
"""

import gc
import sys
import os

# Add local dir to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from nova_utils.interfaces.server_module import Processor
from nova_utils.utils.cache_utils import get_file
from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionInstructPix2PixPipeline, EulerAncestralDiscreteScheduler
from diffusers.utils import load_image
import numpy as np
from PIL import Image as PILImage
from lora import build_lora_xl



# Setting defaults
_default_options = {"model": "stabilityai/stable-diffusion-xl-refiner-1.0", "strength" : "0.58", "guidance_scale" : "11.0", "n_steps" : "30", "lora": "","lora_weight": "0.5" }

# TODO: add log infos, 
class StableDiffusionXL(Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = _default_options | self.options
        self.device = None
        self.ds_iter = None
        self.current_session = None
       

        # IO shortcuts
        self.input = [x for x in self.model_io if x.io_type == "input"]
        self.output = [x for x in self.model_io if x.io_type == "output"]
        self.input = self.input[0]
        self.output = self.output[0]

    def process_data(self, ds_iter) -> dict:
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.ds_iter = ds_iter
        current_session_name = self.ds_iter.session_names[0]
        self.current_session = self.ds_iter.sessions[current_session_name]['manager']      
        #input_image_url = self.current_session.input_data['input_image_url'].data
        #input_image_url = ' '.join(input_image_url)
        input_image = self.current_session.input_data['input_image'].data
        input_prompt = self.current_session.input_data['input_prompt'].data
        input_prompt = ' '.join(input_prompt)
        negative_prompt = self.current_session.input_data['negative_prompt'].data
        negative_prompt = ' '.join(negative_prompt)
       # print("Input Image: " + input_image_url)
        print("Input prompt: " + input_prompt)
        print("Negative prompt: " + negative_prompt)

        try:

            model = self.options['model']
            lora = self.options['lora']
            #init_image = load_image(input_image_url).convert("RGB")
            init_image =  PILImage.fromarray(input_image)

            mwidth = 1024
            mheight = 1024
            w = mwidth
            h = mheight
            if init_image.width > init_image.height:
                scale = float(init_image.height / init_image.width)
                w = mwidth
                h = int(mheight * scale)
            elif init_image.width < init_image.height:
                scale = float(init_image.width / init_image.height)
                w = int(mwidth * scale)
                h = mheight
            else:
                w = mwidth
                h = mheight

            init_image = init_image.resize((w, h))

            if lora != "" and lora != "None":
                print("Loading lora...")

                lora, input_prompt, existing_lora = build_lora_xl(lora, input_prompt, "" )

                from diffusers import AutoPipelineForImage2Image
                import torch



                #init_image = init_image.resize((int(w/2), int(h/2)))

                pipe = AutoPipelineForImage2Image.from_pretrained(
                    "stabilityai/stable-diffusion-xl-base-1.0",
                    torch_dtype=torch.float16).to("cuda")

                if existing_lora:
                    lora_uri = [ x for x in self.trainer.meta_uri if x.uri_id == lora][0]
                    if str(lora_uri) == "":
                        return  "Lora not found"
                    lora_path = get_file(
                        fname=str(lora_uri.uri_id) + ".safetensors",
                        origin=lora_uri.uri_url,
                        file_hash=lora_uri.uri_hash,
                        cache_dir=os.getenv("CACHE_DIR"),
                        tmp_dir=os.getenv("TMP_DIR"),
                        )
                    pipe.load_lora_weights(str(lora_path))
                    print("Loaded Lora: " + str(lora_path))

                seed = 20000
                generator = torch.manual_seed(seed)

                #os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
            
                image = pipe(
                    prompt=input_prompt,
                    negative_prompt=negative_prompt,
                    image=init_image,
                    generator=generator,
                    num_inference_steps=int(self.options['n_steps']), 
                    image_guidance_scale=float(self.options['guidance_scale']),
                    strength=float(str(self.options['strength']))).images[0]


            elif model == "stabilityai/stable-diffusion-xl-refiner-1.0":

                pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
                    model, torch_dtype=torch.float16, variant="fp16",
                    use_safetensors=True
                )

                n_steps = int(self.options['n_steps'])
                transformation_strength = float(self.options['strength'])
                cfg_scale = float(self.options['guidance_scale'])

                pipe = pipe.to(self.device)
                image = pipe(input_prompt, image=init_image,
                            negative_prompt=negative_prompt, num_inference_steps=n_steps, strength=transformation_strength, guidance_scale=cfg_scale).images[0]
            
            elif model == "timbrooks/instruct-pix2pix":
                pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(model, torch_dtype=torch.float16,
                                                                            safety_checker=None)

                pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)

                pipe.to(self.device)
                n_steps = int(self.options['n_steps'])
                cfg_scale = float(self.options['guidance_scale'])
                image = pipe(input_prompt, negative_prompt=negative_prompt, image=init_image, num_inference_steps=n_steps, image_guidance_scale=cfg_scale).images[0]


            if torch.cuda.is_available():
                del pipe
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

      
            numpy_array = np.array(image)
            return numpy_array


        except Exception as e:
            print(e)
            sys.stdout.flush()
            return "Error"

    
    def to_output(self, data: dict):
        self.current_session.output_data_templates['output_image'].data = data
        return self.current_session.output_data_templates


  