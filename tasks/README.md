# NostrAI Data Vending Machine Tasks

Here Tasks can be defined. Tasks need to follow the DVMTaskInterface as defined in interfaces. 
Tasks can either happen locally (especially if they are fast) or they can call an alternative backend.
Reusable backend functions can be defined in backends (e.g. API calls)

Current List of Tasks:

| Module               | Kind | Description                               | Backend                   |
|----------------------|------|-------------------------------------------|---------------------------|
| Translation          | 5002 | Translates Inputs to another language     | Local, calling Google API |
| TextExtractionPDF    | 5001 | Extracts Text from a PDF file             | Local                     |
| ImageGenerationSDXL  | 5100 | Generates an Image with StableDiffusionXL | nova-server               |
| ImageGenerationDALLE | 5100 | Generates an Image with Dall-E            | OpenAI                    |
