"""StableDiffusionXL Module
"""
import gc
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


from nova_utils.interfaces.server_module import Processor

# Setting defaults
_default_options = {"kind": "prompt", "mode": "fast" }

# TODO: add log infos, 
class ImageInterrogator(Processor):
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

        from PIL import Image as PILImage
        import torch

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.ds_iter = ds_iter
        current_session_name = self.ds_iter.session_names[0]
        self.current_session = self.ds_iter.sessions[current_session_name]['manager']      
        #os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
        kind =  self.options['kind'] #"prompt" #"analysis" #prompt
        mode = self.options['mode']
        #url = self.current_session.input_data['input_image_url'].data[0]
        #print(url)
        input_image = self.current_session.input_data['input_image'].data
        init_image =  PILImage.fromarray(input_image)
        mwidth = 256
        mheight = 256


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

        from clip_interrogator import Config, Interrogator

        config = Config(clip_model_name="ViT-L-14/openai", device="cuda")


        if kind == "analysis":
            ci = Interrogator(config)


            image_features = ci.image_to_features(init_image)

            top_mediums = ci.mediums.rank(image_features, 5)
            top_artists = ci.artists.rank(image_features, 5)
            top_movements = ci.movements.rank(image_features, 5)
            top_trendings = ci.trendings.rank(image_features, 5)
            top_flavors = ci.flavors.rank(image_features, 5)

            medium_ranks = {medium: sim for medium, sim in zip(top_mediums, ci.similarities(image_features, top_mediums))}
            artist_ranks = {artist: sim for artist, sim in zip(top_artists, ci.similarities(image_features, top_artists))}
            movement_ranks = {movement: sim for movement, sim in
                            zip(top_movements, ci.similarities(image_features, top_movements))}
            trending_ranks = {trending: sim for trending, sim in
                            zip(top_trendings, ci.similarities(image_features, top_trendings))}
            flavor_ranks = {flavor: sim for flavor, sim in zip(top_flavors, ci.similarities(image_features, top_flavors))}

            result = "Medium Ranks:\n" + str(medium_ranks) + "\nArtist Ranks: " + str(artist_ranks) +  "\nMovement Ranks:\n" + str(movement_ranks) + "\nTrending Ranks:\n" + str(trending_ranks) +  "\nFlavor Ranks:\n" + str(flavor_ranks)

            print(result)
            return result
        else:

            ci = Interrogator(config)
            ci.config.blip_num_beams = 64
            ci.config.chunk_size = 2024
            ci.config.clip_offload = True
            ci.config.apply_low_vram_defaults()
            #MODELS = ['ViT-L (best for Stable Diffusion 1.*)']
            ci.config.flavor_intermediate_count = 2024 #if clip_model_name == MODELS[0] else 1024

            image = init_image
            if mode == 'best':
                prompt = ci.interrogate(image)
            elif mode == 'classic':
                prompt = ci.interrogate_classic(image)
            elif mode == 'fast':
                prompt = ci.interrogate_fast(image)
            elif mode == 'negative':
                prompt = ci.interrogate_negative(image)

            #print(str(prompt))
            return prompt


    # config = Config(clip_model_name=os.environ['TRANSFORMERS_CACHE'] + "ViT-L-14/openai", device="cuda")git
    # ci = Interrogator(config)
        # "ViT-L-14/openai"))
        # "ViT-g-14/laion2B-s34B-b88K"))

    
    def to_output(self, data: dict):
        import numpy as np
        self.current_session.output_data_templates['output'].data = np.array([data])
        return self.current_session.output_data_templates