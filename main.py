import os
from pathlib import Path
from threading import Thread

import dotenv
import utils.env as env
from utils.definitions import EventDefinitions


def run_nostr_dvm_with_local_config():
    from dvm import dvm, DVMConfig
    from utils.nip89_utils import NIP89Announcement


    dvmconfig = DVMConfig()
    dvmconfig.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)
    dvmconfig.SUPPORTED_TASKS = ["translation"]
    dvmconfig.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvmconfig.LNBITS_URL = os.getenv(env.LNBITS_HOST)

    nip89translation = NIP89Announcement()
    nip89translation.kind = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    nip89translation.dtag = os.getenv(env.TASK_TRANSLATION_NIP89_DTAG)
    nip89translation.pk = os.getenv(env.NOSTR_PRIVATE_KEY)
    nip89translation.content = "{\"name\":\"NostrAI DVM Translator\",\"image\":\"https://cdn.nostr.build/i/feb98d8700abe7d6c67d9106a72a20354bf50805af79869638f5a32d24a5ac2a.jpg\",\"about\":\"Translates Text from given text/event/job, currently using Google Translation Services into language defined in param.  \",\"nip90Params\":{\"language\":{\"required\":true,\"values\":[\"af\",\"am\",\"ar\",\"az\",\"be\",\"bg\",\"bn\",\"bs\",\"ca\",\"ceb\",\"co\",\"cs\",\"cy\",\"da\",\"de\",\"el\",\"eo\",\"es\",\"et\",\"eu\",\"fa\",\"fi\",\"fr\",\"fy\",\"ga\",\"gd\",\"gl\",\"gu\",\"ha\",\"haw\",\"hi\",\"hmn\",\"hr\",\"ht\",\"hu\",\"hy\",\"id\",\"ig\",\"is\",\"it\",\"he\",\"ja\",\"jv\",\"ka\",\"kk\",\"km\",\"kn\",\"ko\",\"ku\",\"ky\",\"la\",\"lb\",\"lo\",\"lt\",\"lv\",\"mg\",\"mi\",\"mk\",\"ml\",\"mn\",\"mr\",\"ms\",\"mt\",\"my\",\"ne\",\"nl\",\"no\",\"ny\",\"or\",\"pa\",\"pl\",\"ps\",\"pt\",\"ro\",\"ru\",\"sd\",\"si\",\"sk\",\"sl\",\"sm\",\"sn\",\"so\",\"sq\",\"sr\",\"st\",\"su\",\"sv\",\"sw\",\"ta\",\"te\",\"tg\",\"th\",\"tl\",\"tr\",\"ug\",\"uk\",\"ur\",\"uz\",\"vi\",\"xh\",\"yi\",\"yo\",\"zh\",\"zu\"]}}}"
    dvmconfig.NIP89s.append(nip89translation)


    nostr_dvm_thread = Thread(target=dvm, args=[dvmconfig])
    nostr_dvm_thread.start()


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')



    run_nostr_dvm_with_local_config()




