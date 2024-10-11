# WhisperX

This modules provides fast automatic speech recognition (70x realtime with large-v2) with word-level timestamps and
speaker diarization.

* https://github.com/m-bain/whisperX

## Options

- `model`: string, identifier of the model to choose, sorted ascending in required (V)RAM:
    - `tiny`, `tiny.en`
    - `base`, `base.en`
    - `small`, `small.en`
    - `medium`, `medium.en`
    - `large-v1`
    - `large-v2`

- `alignment_mode`: string, alignment method to use
    - `raw` Segments as identified by Whisper
    - `segment` Improved segmentation using separate alignment model. Roughly equivalent to sentence alignment.
    - `word` Improved segmentation using separate alignment model. Equivalent to word alignment.

- `language`: language code for transcription and alignment models. Supported languages:
    - `ar`, `cs`, `da`, `de`, `el`, `en`, `es`, `fa`, `fi`, `fr`, `he`, `hu`, `it`, `ja`, `ko`, `nl`, `pl`, `pt`, `ru`,
      `te`, `tr`, `uk`, `ur`, `vi`, `zh`
    - `None`: auto-detect language from first 30 seconds of audio

- `batch_size`: how many samples to process at once, increases speed but also (V)RAM consumption

## Examples

### Request

```python
import requests
import json

payload = {
  "jobID" : "whisper_transcript",
  "data": json.dumps([
    {"src":"file:stream:audio", "type":"input", "id":"audio", "uri":"path/to/my/file.wav"},
    {"src":"file:annotation:free", "type":"output", "id":"transcript",  "uri":"path/to/my/transcript.annotation"}
  ]),
  "trainerFilePath": "modules\\whisperx\\whisperx_transcript.trainer",
}


url = 'http://127.0.0.1:8080/process'
headers = {'Content-type': 'application/x-www-form-urlencoded'}
x = requests.post(url, headers=headers, data=payload)
print(x.text)

```
