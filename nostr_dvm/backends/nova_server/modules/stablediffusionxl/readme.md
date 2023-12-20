# Stable Diffusion XL

This modules provides image generation based on prompts

* https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

## Options

- `model`: string, identifier of the model to choose
    - `stabilityai/stable-diffusion-xl-base-1.0`: Default Stable Diffusion XL model


- `ratio`: Ratio of the output image
    - `1-1` ,`4-3`, `16-9`, `16-10`, `3-4`,`9-16`,`10-16`

- `high_noise_frac`: Denoising factor
 
- `n_steps`: how many iterations should be performed

## Example payload

```python
payload = {
    'trainerFilePath': 'modules\\stablediffusionxl\\stablediffusionxl.trainer',
    'server': '127.0.0.1',
    'data' = '[{"id":"input_prompt","type":"input","src":"user:text","prompt":"' + prompt +'","active":"True"},{"id":"negative_prompt","type":"input","src":"user:text","prompt":"' +  negative_prompt +'","active":"True"},{"id":"output_image","type":"output","src":"file:image","uri":"' + outputfile+'","active":"True"}]'
    'optStr': 'model=stabilityai/stable-diffusion-xl-base-1.0;ratio=4-3'
}

import requests

url = 'http://127.0.0.1:53770/predict'
headers = {'Content-type': 'application/x-www-form-urlencoded'}
requests.post(url, headers=headers, data=payload)
```
