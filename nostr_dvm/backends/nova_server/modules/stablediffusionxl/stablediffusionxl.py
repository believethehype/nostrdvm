"""StableDiffusionXL Module
"""
import gc
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from ssl import Options
from nova_utils.interfaces.server_module import Processor
from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline, logging
from compel import Compel, ReturnedEmbeddingsType
from nova_utils.utils.cache_utils import get_file
import numpy as np
PYTORCH_ENABLE_MPS_FALLBACK = 1

import torch
from PIL import Image
from lora import build_lora_xl
logging.disable_progress_bar()
logging.enable_explicit_format()
#logging.set_verbosity_info()


# Setting defaults
_default_options = {"model": "stabilityai/stable-diffusion-xl-base-1.0", "ratio": "1-1", "width": "", "height":"", "high_noise_frac" : "0.8", "n_steps" : "35", "lora" : "" }

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
        self._device = ("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_built() else "cpu"))
        self.variant = "fp16"
        self.torch_d_type = torch.float16
        self.ds_iter = ds_iter
        current_session_name = self.ds_iter.session_names[0]
        self.current_session = self.ds_iter.sessions[current_session_name]['manager']      
        input_prompt = self.current_session.input_data['input_prompt'].data
        input_prompt = ' '.join(input_prompt)
        negative_prompt = self.current_session.input_data['negative_prompt'].data
        negative_prompt = ' '.join(negative_prompt)
        new_width = 0
        new_height = 0
        print("Input prompt: " + input_prompt)
        print("Negative prompt: " + negative_prompt)

        try:
            if self.options['width'] != "" and self.options['height'] != "":
                new_width = int(self.options['width'])
                new_height = int(self.options['height'])                        
                ratiow, ratioh =  self.calculate_aspect(new_width, new_height) 
                print("Ratio:" + str(ratiow) + ":" + str(ratioh))

            else:
                ratiow = str(self.options['ratio']).split('-')[0]
                ratioh =str(self.options['ratio']).split('-')[1]

            model = self.options["model"]
            lora = self.options["lora"]
            mwidth = 1024
            mheight = 1024

            height = mheight
            width = mwidth

            ratiown = int(ratiow)
            ratiohn= int(ratioh)

            if ratiown > ratiohn:
                height = int((ratiohn/ratiown) * float(width))
            elif ratiown < ratiohn:
                width = int((ratiown/ratiohn) * float(height))
            elif ratiown == ratiohn:
                width = height

        
            print("Processing Output width: " + str(width) + " Output height: " + str(height))

          


            if model == "stabilityai/stable-diffusion-xl-base-1.0":
                base = StableDiffusionXLPipeline.from_pretrained(model, torch_dtype=self.torch_d_type, variant=self.variant, use_safetensors=True).to(self.device)
                print("Loaded model: " + model)

            else:
                 
                model_uri = [ x for x in self.trainer.meta_uri if x.uri_id == model][0]
                if str(model_uri) == "":
                    return  "Model not found"

                model_path = get_file(
                    fname=str(model_uri.uri_id) + ".safetensors",
                    origin=model_uri.uri_url,
                    file_hash=model_uri.uri_hash,
                    cache_dir=os.getenv("CACHE_DIR"),
                    tmp_dir=os.getenv("TMP_DIR"),
                    )
                
                print(str(model_path))


                base = StableDiffusionXLPipeline.from_single_file(str(model_path), torch_dtype=self.torch_d_type, variant=self.variant, use_safetensors=True).to(self.device)
                print("Loaded model: " + model)

            if lora != "" and lora != "None":
                print("Loading lora...")          
                lora, input_prompt, existing_lora =  build_lora_xl(lora, input_prompt, "")

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
                    
                    base.load_lora_weights(str(lora_path))
                    print("Loaded Lora: " + str(lora_path))

            refiner = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=base.text_encoder_2,
            vae=base.vae,
            torch_dtype=self.torch_d_type,
            use_safetensors=True,
            variant=self.variant,
            )

            
            compel_base = Compel(
                tokenizer=[base.tokenizer, base.tokenizer_2],
                text_encoder=[base.text_encoder, base.text_encoder_2],
                returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
                requires_pooled=[False, True],
            )

            compel_refiner = Compel(
                tokenizer=[refiner.tokenizer_2],
                text_encoder=[refiner.text_encoder_2],
                returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
                requires_pooled=[True])

            conditioning, pooled = compel_base(input_prompt)
            negative_conditioning, negative_pooled = compel_base(negative_prompt)

            conditioning_refiner, pooled_refiner = compel_refiner(input_prompt)
            negative_conditioning_refiner, negative_pooled_refiner = compel_refiner(
                negative_prompt)
        
            
            n_steps = int(self.options['n_steps'])
            high_noise_frac = float(self.options['high_noise_frac'])


            #base.unet = torch.compile(base.unet, mode="reduce-overhead", fullgraph=True)



            img = base(
                prompt_embeds=conditioning,
                pooled_prompt_embeds=pooled,
                negative_prompt_embeds=negative_conditioning,
                negative_pooled_prompt_embeds=negative_pooled,
                width=width,
                height=height,
                num_inference_steps=n_steps,
                denoising_end=high_noise_frac,
                output_type="latent",
            ).images

            if torch.cuda.is_available():
                del base
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

            refiner.to(self.device)
            # refiner.enable_model_cpu_offload()
            image = refiner(
                prompt_embeds=conditioning_refiner,
                pooled_prompt_embeds=pooled_refiner,
                negative_prompt_embeds=negative_conditioning_refiner,
                negative_pooled_prompt_embeds=negative_pooled_refiner,
                num_inference_steps=n_steps,
                denoising_start=high_noise_frac,
                num_images_per_prompt=1,
                image=img,
            ).images[0]

            if torch.cuda.is_available():
                del refiner
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

            if new_height != 0 or new_width != 0 and (new_width != mwidth or new_height != mheight) :
                print("Resizing to width: " + str(new_width) + " height: " + str(new_height))
                image = image.resize((new_width, new_height), Image.LANCZOS)
    
            numpy_array = np.array(image)
            return numpy_array


        except Exception as e:
            print(e)
            sys.stdout.flush()
            return "Error"
        
    def calculate_aspect(self, width: int, height: int):
        def gcd(a, b):
            """The GCD (greatest common divisor) is the highest number that evenly divides both width and height."""
            return a if b == 0 else gcd(b, a % b)

        r = gcd(width, height)
        x = int(width / r)
        y = int(height / r)

        return x, y


    
    def to_output(self, data: dict):
        self.current_session.output_data_templates['output_image'].data = data
        return self.current_session.output_data_templates