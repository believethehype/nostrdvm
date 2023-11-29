import json
from threading import Thread

from nostr_sdk import Keys

from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Announcement, NIP89Config
from core.dvm import DVM


class DVMTaskInterface:
    NAME: str
    KIND: int
    TASK: str
    FIX_COST: float = 0
    PER_UNIT_COST: float = 0
    PRIVATE_KEY: str
    PUBLIC_KEY: str
    DVM = DVM
    dvm_config: DVMConfig
    admin_config: AdminConfig

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, admin_config: AdminConfig = None,
                 options=None):
        self.init(name, dvm_config, admin_config, nip89config)
        self.options = options

    def init(self, name, dvm_config, admin_config=None, nip89config=None):
        self.NAME = name
        self.PRIVATE_KEY = dvm_config.PRIVATE_KEY
        if dvm_config.PUBLIC_KEY == "" or dvm_config.PUBLIC_KEY is None:
            dvm_config.PUBLIC_KEY = Keys.from_sk_str(dvm_config.PRIVATE_KEY).public_key().to_hex()
        self.PUBLIC_KEY = dvm_config.PUBLIC_KEY
        if dvm_config.FIX_COST is not None:
            self.FIX_COST = dvm_config.FIX_COST
        if dvm_config.PER_UNIT_COST is not None:
            self.PER_UNIT_COST = dvm_config.PER_UNIT_COST

        dvm_config.SUPPORTED_DVMS = [self]
        dvm_config.DB = "db/" + self.NAME + ".db"
        dvm_config.NIP89 = self.NIP89_announcement(nip89config)
        self.dvm_config = dvm_config
        self.admin_config = admin_config


    def run(self):
        nostr_dvm_thread = Thread(target=self.DVM, args=[self.dvm_config, self.admin_config])
        nostr_dvm_thread.start()

    def NIP89_announcement(self, nip89config: NIP89Config):
        nip89 = NIP89Announcement()
        nip89.name = self.NAME
        nip89.kind = self.KIND
        nip89.pk = self.PRIVATE_KEY
        nip89.dtag = nip89config.DTAG
        nip89.content = nip89config.CONTENT
        return nip89

    def is_input_supported(self, tags) -> bool:
        """Check if input is supported for current Task."""
        pass



    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None) -> dict:
        """Parse input into a request form that will be given to the process method"""
        pass

    def process(self, request_form):
        "Process the data and return the result"
        pass

    @staticmethod
    def set_options(request_form):
        print("Setting options...")
        opts = []
        if request_form.get("options"):
            opts = json.loads(request_form["options"])
            print(opts)
        return dict(opts)
