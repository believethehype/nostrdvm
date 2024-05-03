# NostrAI Data Vending Machine Tasks

Here Tasks can be defined. Tasks need to follow the DVMTaskInterface as defined in interfaces. 
Tasks can either happen locally (especially if they are fast) or they can call an alternative backend.
Reusable backend functions can be defined in backends (e.g. API calls)

Current List of Tasks:

| Module                               | Kind | Description                                                | Backend          |
|--------------------------------------|------|------------------------------------------------------------|------------------| 
| TextExtractionPDF                    | 5000 | Extracts Text from a PDF file                              | local            |
| SpeechToTextGoogle                   | 5000 | Extracts Speech from Media files via Google Services       | googleAPI        |
| SpeechToTextWhisperX                 | 5000 | Extracts Speech from Media files via local WhisperX        | nserver          |
| ImageInterrogator                    | 5000 | Extracts Prompts from Images                               | nserver          |
| TextSummarizationHuggingChat         | 5001 | Summarizes given Input                                     | huggingface      |
| **TextSummarizationUnleasedChat**    | 5001 | Summarizes given Input                                     | unleashed api    |
| TranslationGoogle                    | 5002 | Translates Inputs to another language                      | googleAPI        |
| TranslationLibre                     | 5002 | Translates Inputs to another language                      | libreAPI         |
| TextGenerationLLMLite                | 5050 | Chat with LLM backends like Ollama, ChatGPT etc            | local/api/openai |
| TextGenerationHuggingChat            | 5050 | Chat with LLM backend on Huggingface                       | huggingface      |
| TextGenerationLLMUnleashedChat       | 5050 | Chat with unleashed.chat LLMs                              | unleashed api    |
| ImageGenerationSDXL                  | 5100 | Generates an Image from Prompt with Stable Diffusion XL    | nserver          |
| ImageGenerationSDXLIMG2IMG           | 5100 | Generates an Image from an Image with Stable Diffusion XL  | nserver          |
| ImageGenerationReplicateSDXL         | 5100 | Generates an Image from Prompt with Stable Diffusion XL    | replicate        |
| ImageGenerationMLX                   | 5100 | Generates an Image with Stable Diffusion 2.1 on M1/2/3 Mac | mlx              |
| ImageGenerationDALLE                 | 5100 | Generates an Image with OpenAI's Dall-E                    | openAI           |
| ImageUpscale                         | 5100 | Upscales an Image                                          | nserver          |
| MediaConverter                       | 5200 | Converts a link of a media file and uploads it             | openAI           |
| VideoGenerationReplicateSVD          | 5202 | Generates a Video from an Image                            | replicate        |
| VideoGenerationSVD                   | 5202 | Generates a Video from an Image                            | nserver          |
| TextToSpeech                         | 5250 | Generate Audio from a prompt                               | local            |
| TrendingNotesNostrBand               | 5300 | Show trending notes on nostr.band                          | nostr.band api   |
| **Discover Currently Popular Notes** | 5300 | Show trending notes in the last 2 hours                    | local/db         |
| **Discover CPN Followers**           | 5300 | Show trending notes by people you follow                   | local/db         |
| DiscoverInactiveFollows              | 5301 | Find inactive Nostr users                                  | local            |
| **DiscoverNonFollows**               | 5301 | Find Nostr users  not following back                       | local            |
| **Discover Bot Farms**               | 5301 | Find Bots, so you can mute them                            | local            |
| **Discover Censor WOT**              | 5301 | Find users that have been reported by your follows/WOT     | local            |
| AdvancedSearch                       | 5302 | Search Content on relays (nostr.band)                      | local/nostr.band |
| AdvancedSearchWine                   | 5302 | Search Content on nostr.wine                               | api/nostr.wine   |
| **Search Users**                     | 5303 | Search Users based on search terms                         | local/db         |
| **Subscriptions**                    | 5906 | Manage Subscriptions for other DVMS                        | local            |

Kinds with (inoff) are suggestions and not merged yet and might change in the future.
Backends might require to add an API key to the .env file or run an external server/framework the dvm will communicate with.