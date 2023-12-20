# NostrAI Data Vending Machine Tasks

Here Tasks can be defined. Tasks need to follow the DVMTaskInterface as defined in interfaces. 
Tasks can either happen locally (especially if they are fast) or they can call an alternative backend.
Reusable backend functions can be defined in backends (e.g. API calls)

Current List of Tasks:

| Module                       | Kind         | Description                                                | Backend          |
|------------------------------|--------------|------------------------------------------------------------|------------------| 
| TextExtractionPDF            | 5000         | Extracts Text from a PDF file                              | local            |
| SpeechToTextGoogle           | 5000         | Extracts Speech from Media files via Google Services       | googleAPI        |
| SpeechToTextWhisperX         | 5000         | Extracts Speech from Media files via local WhisperX        | nserver          |
| ImageInterrogator            | 5000         | Extracts Prompts from Images                               | nserver          |
| TranslationGoogle            | 5002         | Translates Inputs to another language                      | googleAPI        |
| TranslationLibre             | 5002         | Translates Inputs to another language                      | libreAPI         |
| TextGenerationLLMLite        | 5050         | Chat with LLM backends like Ollama, ChatGPT etc            | local/api/openai |
| ImageGenerationSDXL          | 5100         | Generates an Image from Prompt with Stable Diffusion XL    | nserver          |
| ImageGenerationSDXLIMG2IMG   | 5100         | Generates an Image from an Image with Stable Diffusion XL  | nserver          |
| ImageGenerationReplicateSDXL | 5100         | Generates an Image from Prompt with Stable Diffusion XL    | replicate        |
| ImageGenerationMLX           | 5100         | Generates an Image with Stable Diffusion 2.1 on M1/2/3 Mac | mlx              |
| ImageGenerationDALLE         | 5100         | Generates an Image with OpenAI's Dall-E                    | openAI           |
| ImageUpscale                 | 5100         | Upscales an Image                                          | nserver          |
| MediaConverter               | 5200         | Converts a link of a media file and uploads it             | openAI           |
| VideoGenerationReplicateSVD  | 5202 (inoff) | Generates a Video from an Image                            | replicate        |
| TextToSpeech                 | 5250 (inoff) | Generate Audio from a prompt                               | local            |
| TrendingNotesNostrBand       | 5300         | Show trending notes on nostr.band                          | nostr.band api   |
| DiscoverInactiveFollows      | 5301         | Find inactive Nostr users                                  | local            |
| AdvancedSearch               | 5302 (inoff) | Search Content on nostr.band                               | local            |

Kinds with (inoff) are suggestions and not merged yet and might change in the future.
Backends might require to add an API key to the .env file or run an external server/framework the dvm will communicate with.