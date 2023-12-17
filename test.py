import json

import nostr_dvm
from nostr_dvm.tasks.texttospeech import TextToSpeech
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag

identifier = "tts"
name = "Guy Swann Clone"

dvm_config = build_default_config(identifier)
admin_config = AdminConfig()
admin_config.REBROADCAST_NIP89 = False
admin_config.UPDATE_PROFILE = False
admin_config.LUD16 = dvm_config.LN_ADDRESS

#Use default file if paramter is empty, else overwrite with any local wav file
options = {'input_file': ""}

nip89info = {
    "name": name,
    "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
    "about": "I Generate Speech from Text",
    "encryptionSupported": True,
    "cashuAccepted": True,
    "nip90Params": {
        "language": {
            "required": False,
            "values": []
        }
    }
}

nip89config = NIP89Config()
nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
nip89config.CONTENT = json.dumps(nip89info)

tts = TextToSpeech(name=name,
                   dvm_config=dvm_config,
                   nip89config=nip89config,
                   admin_config=admin_config,
                   options=options)
tts.run()