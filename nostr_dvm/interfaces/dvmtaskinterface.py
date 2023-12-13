import json
import subprocess
import sys
from threading import Thread

from nostr_sdk import Keys

from nostr_dvm.dvm import DVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.output_utils import post_process_result


class DVMTaskInterface:
    NAME: str
    KIND: int
    TASK: str = ""
    FIX_COST: float = 0
    PER_UNIT_COST: float = 0
    PRIVATE_KEY: str
    PUBLIC_KEY: str
    DVM = DVM
    SUPPORTS_ENCRYPTION = True  # DVMs build with this framework support encryption, but others might not.
    ACCEPTS_CASHU = True  # DVMs build with this framework support encryption, but others might not.
    dvm_config: DVMConfig
    admin_config: AdminConfig
    dependencies = []

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, admin_config: AdminConfig = None,
                 options=None, task=None):
        self.init(name, dvm_config, admin_config, nip89config, task)
        self.options = options
        self.install_dependencies(self.dependencies)

    def init(self, name, dvm_config, admin_config=None, nip89config=None, task=None):
        self.NAME = name
        self.PRIVATE_KEY = dvm_config.PRIVATE_KEY
        if dvm_config.PUBLIC_KEY == "" or dvm_config.PUBLIC_KEY is None:
            dvm_config.PUBLIC_KEY = Keys.from_sk_str(dvm_config.PRIVATE_KEY).public_key().to_hex()
        self.PUBLIC_KEY = dvm_config.PUBLIC_KEY
        if dvm_config.FIX_COST is not None:
            self.FIX_COST = dvm_config.FIX_COST
        if dvm_config.PER_UNIT_COST is not None:
            self.PER_UNIT_COST = dvm_config.PER_UNIT_COST
        if task is not None:
            self.TASK = task

        dvm_config.SUPPORTED_DVMS = [self]
        dvm_config.DB = "db/" + self.NAME + ".db"
        if nip89config.KIND is not None:
            self.KIND = nip89config.KIND

        dvm_config.NIP89 = self.NIP89_announcement(nip89config)
        self.dvm_config = dvm_config
        self.admin_config = admin_config

    def run(self):
        nostr_dvm_thread = Thread(target=self.DVM, args=[self.dvm_config, self.admin_config])
        nostr_dvm_thread.start()

    def NIP89_announcement(self, nip89config: NIP89Config):
        nip89 = NIP89Config()
        nip89.NAME = self.NAME
        nip89.KIND = self.KIND
        nip89.PK = self.PRIVATE_KEY
        nip89.DTAG = nip89config.DTAG
        nip89.CONTENT = nip89config.CONTENT
        return nip89

    def is_input_supported(self, tags) -> bool:
        """Check if input is supported for current Task."""
        pass

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None) -> dict:
        """Parse input into a request form that will be given to the process method"""
        pass

    def process(self, request_form):
        "Process the data and return the result"
        pass

    def post_process(self, result, event):
        """Post-process the data and return the result Use default function, if not overwritten"""
        return post_process_result(result, event)

    def install_dependencies(self, packages):
        import pip
        for package in packages:
            try:
                __import__(package.split("=")[0])
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    @staticmethod
    def set_options(request_form):
        print("Setting options...")
        opts = []
        if request_form.get("options"):
            opts = json.loads(request_form["options"])
            print(opts)
        return dict(opts)
