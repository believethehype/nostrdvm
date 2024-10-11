import gc
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from nova_utils.interfaces.server_module import Processor
import torch
from diffusers import StableVideoDiffusionPipeline
import numpy as np
from PIL import Image as PILImage

# Setting defaults
_default_options = {"model": "stabilityai/stable-video-diffusion-img2vid-xt", "fps": "7", "seed": ""}


# TODO: add log infos,
class StableVideoDiffusion(Processor):
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

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.ds_iter = ds_iter
        current_session_name = self.ds_iter.session_names[0]
        self.current_session = self.ds_iter.sessions[current_session_name]['manager']
        input_image = self.current_session.input_data['input_image'].data

        try:
            pipe = StableVideoDiffusionPipeline.from_pretrained(
                self.options["model"], torch_dtype=torch.float16, variant="fp16"
            )
            pipe.enable_model_cpu_offload()

            # Load the conditioning image
            image = PILImage.fromarray(input_image)
            image = image.resize((1024, 576))

            if self.options["seed"] != "" and self.options["seed"] != " ":
                generator = torch.manual_seed(int(self.options["seed"]))
                frames = pipe(image, decode_chunk_size=8, generator=generator).frames[0]
            else:
                frames = pipe(image, decode_chunk_size=8).frames[0]

            if torch.cuda.is_available():
                del pipe
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

            np_video = np.stack([np.asarray(x) for x in frames])
            return np_video


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

    def to_output(self, data: list):
        video = self.current_session.output_data_templates['output_video']
        video.data = data
        video.meta_data.sample_rate = int(self.options['fps'])
        video.meta_data.media_type = 'video'

        return self.current_session.output_data_templates
