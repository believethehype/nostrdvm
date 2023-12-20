"""WhisperX Module
"""
from nova_utils.interfaces.server_module import Processor
import sys

# Setting defaults
_default_options = {"model": "tiny", "alignment_mode": "segment", "batch_size": "16", 'language': None, 'compute_type': 'float16'}

# supported language codes, cf. whisperx/alignment.py
# DEFAULT_ALIGN_MODELS_TORCH.keys() | DEFAULT_ALIGN_MODELS_HF.keys() | {None}
# {'vi', 'uk', 'pl', 'ur', 'ru', 'ko', 'en', 'zh', 'es', 'it', 'el', 'te', 'da', 'he', 'fa', 'pt', 'de',
#  'fr', 'tr', 'nl', 'cs', 'hu', 'fi', 'ar', 'ja', None}

class WhisperX(Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = _default_options | self.options
        self.device = None
        self.ds_iter = None
        self.session_manager = None

        # IO shortcuts
        self.input = [x for x in self.model_io if x.io_type == "input"]
        self.output = [x for x in self.model_io if x.io_type == "output"]
        assert len(self.input) == 1 and len(self.output) == 1
        self.input = self.input[0]
        self.output = self.output[0]

    def process_data(self, ds_manager) -> dict:
        import whisperx
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.session_manager = self.get_session_manager(ds_manager)
        input_audio = self.session_manager.input_data['audio']

        # sliding window will be applied by WhisperX
        audio = whisperx.load_audio(input_audio.meta_data.file_path)

        # transcribe with original whisper
        try:
            model = whisperx.load_model(self.options["model"], self.device, compute_type=self.options['compute_type'],
                                        language=self.options['language'])
        except ValueError:
            print(f'Your hardware does not support {self.options["compute_type"]} - fallback to float32')
            sys.stdout.flush()
            model = whisperx.load_model(self.options["model"], self.device, compute_type='float32',
                                        language=self.options['language'])
            
        result = model.transcribe(audio, batch_size=int(self.options["batch_size"]))

        # delete model if low on GPU resources
        import gc; gc.collect(); torch.cuda.empty_cache(); del model

        if not self.options["alignment_mode"] == "raw":
            # load alignment model and metadata
            model_a, metadata = whisperx.load_align_model(
                language_code=result["language"], device=self.device
            )

            # align whisper output
            result_aligned = whisperx.align(
                result["segments"], model_a, metadata, audio, self.device
            )
            result = result_aligned

            # delete model if low on GPU resources
            import gc; gc.collect(); torch.cuda.empty_cache(); del model_a

        return result

    def to_output(self, data: dict):
        def _fix_missing_timestamps(data):
            """
            https://github.com/m-bain/whisperX/issues/253
            Some characters might miss timestamps and recognition scores. This function adds estimated time stamps assuming a fixed time per character of 65ms.
            Confidence for each added timestamp will be 0.
            Args:
                data (dictionary): output dictionary as returned by process_data
            """
            last_end = 0
            for s in data["segments"]:
                for w in s["words"]:
                    if "end" in w.keys():
                        last_end = w["end"]
                    else:
                        #TODO: rethink lower bound for confidence; place word centred instead of left aligned
                        w["start"] = last_end
                        last_end += 0.065
                        w["end"] = last_end
                        #w["score"] = 0.000
                        w['score'] = _hmean([x['score'] for x in s['words'] if len(x) == 4])
        
        def _hmean(scores):
            if len(scores) > 0:
                prod = scores[0]
                for s in scores[1:]:
                    prod *= s
                prod = prod**(1/len(scores))
            else:
                prod = 0
            return prod
        
        if (
            self.options["alignment_mode"] == "word"
            or self.options["alignment_mode"] == "segment"
        ):
            _fix_missing_timestamps(data)

        if self.options["alignment_mode"] == "word":
            anno_data = [
                (w["start"], w["end"], w["word"], w["score"])
                for w in data["word_segments"]
            ]
        else:
            anno_data = [
                #(w["start"], w["end"], w["text"], _hmean([x['score'] for x in w['words']])) for w in data["segments"]
                (w["start"], w["end"], w["text"], 1) for w in data["segments"]  # alignment 'raw' no longer contains a score(?)
            ]

        # convert to milliseconds
        anno_data = [(x[0]*1000, x[1]*1000, x[2], x[3]) for x in anno_data]
        out = self.session_manager.output_data_templates[self.output.io_id]
        out.data = anno_data
        return self.session_manager.output_data_templates
