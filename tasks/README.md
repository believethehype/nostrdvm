# NostrAI Data Vending Machine Tasks

Here Tasks can be defined. Tasks need to follow the DVMTaskInterface as defined in interfaces. 
Tasks can either happen locally (especially if they are fast) or they can call an alternative backend.
Reusable backend functions can be defined in backends (e.g. API calls)

Current List of Tasks:

| Module               | Kind | Description                                    | Backend     |
|----------------------|------|------------------------------------------------|-------------| 
| TextExtractionPDF    | 5000 | Extracts Text from a PDF file                  | local       |
| SpeechToTextWhisperX | 5000 | Extracts Speech from Media files               | nova-server |
| TranslationGoogle    | 5002 | Translates Inputs to another language          | google API  |
| TranslationLibre     | 5002 | Translates Inputs to another language          | libre API   |
| ImageGenerationSDXL  | 5100 | Generates an Image with StableDiffusionXL      | nova-server |
| ImageGenerationDALLE | 5100 | Generates an Image with Dall-E                 | openAI      |
| MediaConverter       | 5300 | Converts a link of a media file and uploads it | openAI      |