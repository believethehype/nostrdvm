"""RealESRGan Module
"""

import os
import glob
import sys
from nova_utils.interfaces.server_module import Processor
from basicsr.archs.rrdbnet_arch import RRDBNet
from basicsr.utils.download_util import load_file_from_url
import numpy as np



from realesrgan import RealESRGANer
from realesrgan.archs.srvgg_arch import SRVGGNetCompact
import cv2
from PIL import Image as PILImage


# Setting defaults
_default_options = {"model": "RealESRGAN_x4plus", "outscale": 4, "denoise_strength": 0.5, "tile": 0,"tile_pad": 10,"pre_pad": 0, "compute_type": "fp32", "face_enhance": False }

# TODO: add log infos, 
class RealESRGan(Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = _default_options | self.options
        self.device = None
        self.ds_iter = None
        self.current_session = None
        self.model_path = None #Maybe need this later for manual path
       

        # IO shortcuts
        self.input = [x for x in self.model_io if x.io_type == "input"]
        self.output = [x for x in self.model_io if x.io_type == "output"]
        self.input = self.input[0]
        self.output = self.output[0]

    def process_data(self, ds_iter) -> dict:
        self.ds_iter = ds_iter
        current_session_name = self.ds_iter.session_names[0]
        self.current_session = self.ds_iter.sessions[current_session_name]['manager']
        input_image = self.current_session.input_data['input_image'].data
 

        try:
            model, netscale, file_url = self.manageModel(str(self.options['model']))

            if  self.model_path is not None:
                model_path = self.model_path
            else:
                model_path = os.path.join('weights', self.options['model'] + '.pth')
                if not os.path.isfile(model_path):
                    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
                    for url in file_url:
                        # model_path will be updated
                        model_path = load_file_from_url(
                            url=url, model_dir=os.path.join(ROOT_DIR, 'weights'), progress=True, file_name=None)

             # use dni to control the denoise strength
            dni_weight = None
            if self.options['model'] == 'realesr-general-x4v3' and float(self.options['denoise_strength']) != 1:
                wdn_model_path = model_path.replace('realesr-general-x4v3', 'realesr-general-wdn-x4v3')
                model_path = [model_path, wdn_model_path]
                dni_weight = [float(self.options['denoise_strength']), 1 - float(self.options['denoise_strength'])]

            half = True
            if self.options["compute_type"] == "fp32":
                half=False


            upsampler = RealESRGANer(
            scale=netscale,
            model_path=model_path,
            dni_weight=dni_weight,
            model=model,
            tile= int(self.options['tile']),
            tile_pad=int(self.options['tile_pad']),
            pre_pad=int(self.options['pre_pad']),
            half=half,
            gpu_id=None) #Can be set if multiple gpus are available

            if bool(self.options['face_enhance']):  # Use GFPGAN for face enhancement
                from gfpgan import GFPGANer
                face_enhancer = GFPGANer(
                    model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth',
                    upscale=int(self.options['outscale']),
                    arch='clean',
                    channel_multiplier=2,
                    bg_upsampler=upsampler)
          
            
            pilimage =  PILImage.fromarray(input_image)
            img = cv2.cvtColor(np.array(pilimage), cv2.COLOR_RGB2BGR)
            try:
                if bool(self.options['face_enhance']):
                    _, _, output = face_enhancer.enhance(img, has_aligned=False, only_center_face=False, paste_back=True)
                else:
                    output, _ = upsampler.enhance(img, outscale=int(self.options['outscale']))
            except RuntimeError as error:
                print('Error', error)
                print('If you encounter CUDA out of memory, try to set --tile with a smaller number.')
    
            output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)

            return output
            
   


        except Exception as e:
            print(e)
            sys.stdout.flush()
            return "Error"

    
    def to_output(self, data: dict):
        self.current_session.output_data_templates['output_image'].data = data
        return self.current_session.output_data_templates


    def manageModel(self, model_name):
        if model_name == 'RealESRGAN_x4plus':  # x4 RRDBNet model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth']
        elif model_name == 'RealESRNet_x4plus':  # x4 RRDBNet model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth']
        elif model_name == 'RealESRGAN_x4plus_anime_6B':  # x4 RRDBNet model with 6 blocks
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth']
        elif model_name == 'RealESRGAN_x2plus':  # x2 RRDBNet model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
            netscale = 2
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth']
        elif model_name == 'realesr-animevideov3':  # x4 VGG-style model (XS size)
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4, act_type='prelu')
            netscale = 4
            file_url = ['https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth']
        elif model_name == 'realesr-general-x4v3':  # x4 VGG-style model (S size)
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type='prelu')
            netscale = 4
            file_url = [
                'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth',
                'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth'
            ]
        
        return model, netscale, file_url