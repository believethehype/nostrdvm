import asyncio
import json
import os
import subprocess
import time
from subprocess import run
import sys
from sys import platform
from threading import Thread
from venv import create
from nostr_sdk import Keys, Kind, LogLevel
from nostr_dvm.dvm import DVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_result



class DVMTaskInterface:
    NAME: str
    KIND: Kind
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

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                 admin_config: AdminConfig = None,
                 options=None, task=None):
        if options is None:
            self.options = {}
        else:
            self.options = options
        self.init(name, dvm_config, admin_config, nip88config, nip89config, task)
        self.install_dependencies(dvm_config)

    def init(self, name, dvm_config, admin_config=None, nip88config=None, nip89config=None, task=None, options=None):
        self.NAME = name
        self.PRIVATE_KEY = dvm_config.PRIVATE_KEY
        if dvm_config.PUBLIC_KEY == "" or dvm_config.PUBLIC_KEY is None:
            dvm_config.PUBLIC_KEY = Keys.parse(dvm_config.PRIVATE_KEY).public_key().to_hex()
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

        if nip88config is None:
            dvm_config.NIP88 = None
        else:
            dvm_config.NIP88 = nip88config

        self.dvm_config = dvm_config
        self.admin_config = admin_config

        asyncio.run(self.init_dvm(name, dvm_config, nip89config, nip88config,
                                          admin_config, options))

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):

        pass

    def install_dependencies(self, dvm_config):
        if dvm_config.SCRIPT != "":
            if self.dvm_config.USE_OWN_VENV:
                dir = r'cache/venvs/' + os.path.basename(dvm_config.SCRIPT).split(".py")[0]
                pip_location = 'bin/pip'
                if platform == "win32" or platform == "nt":
                    pip_location = dir + '/Scripts/pip'

                if not os.path.isdir(dir):
                    print("Creating Venv: " + dir)
                    create(dir, with_pip=True, upgrade_deps=False)
                    self.dependencies.append(("nostr-dvm", "nostr-dvm"))
                    for (module, package) in self.dependencies:
                        print("Installing Venv Module: " + module)
                        run([pip_location, "install", "--upgrade", package], cwd=dir)
            else:
                for module, package in self.dependencies:
                    if module != "nostr-dvm":
                        try:
                            __import__(module)
                        except ImportError:
                            print("Installing global Module: " + module)
                            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    async def run_dvm(self, dvm_config, admin_config):
        print("Implement the run dvm function")
        pass

    def run(self, join=False):
        #dvm = DVM(self.dvm_config, self.admin_config)
        #asyncio.run(dvm.run_dvm(self.dvm_config, self.admin_config))
        nostr_dvm_thread = Thread(target=self.DVM, args=[self.dvm_config, self.admin_config], daemon=False)
        nostr_dvm_thread.start()
        if join:
            nostr_dvm_thread.join()

    async def schedule(self, dvm_config):
        """schedule something, e.g. define some time to update or to post, does nothing by default"""
        pass

    def NIP89_announcement(self, nip89config: NIP89Config):
        nip89 = NIP89Config()
        nip89.NAME = self.NAME
        nip89.KIND = self.KIND
        nip89.PK = self.PRIVATE_KEY
        nip89.DTAG = nip89config.DTAG
        nip89.CONTENT = nip89config.CONTENT
        return nip89

    async def is_input_supported(self, tags, client=None, dvm_config=None) -> bool:
        """Check if input is supported for current Task."""
        pass

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None) -> dict:
        """Parse input into a request form that will be given to the process method"""
        pass

    async def process(self, request_form):
        "Process the data and return the result"
        pass

    async def post_process(self, result, event):
        """Post-process the data and return the result Use default function, if not overwritten"""
        return post_process_result(result, event)

    def set_options(self, request_form):
        if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + self.dvm_config.NIP89.NAME + "] " + "Setting options...")
        opts = []
        if request_form.get("options"):
            opts = json.loads(request_form["options"])
            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print("[" + self.dvm_config.NIP89.NAME + "] " + str(opts))
        return dict(opts)

    @staticmethod
    def process_args():
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--request', dest='request')
        parser.add_argument('--identifier', dest='identifier')
        parser.add_argument('--output', dest='output')
        args = parser.parse_args()
        return args

    @staticmethod
    def write_output(result, output):
        with open(os.path.abspath(output), 'w',  encoding="utf8") as f:
            f.write(result)
        # f.close()


def process_venv(identifier):
    args = DVMTaskInterface.process_args()
    dvm_config = build_default_config(args.identifier)
    dvm = identifier(name="", dvm_config=dvm_config, nip89config=NIP89Config(), admin_config=None)
    try:
        result = asyncio.run(dvm.process(json.loads(args.request)))
        DVMTaskInterface.write_output(result, args.output)
    except Exception as e:
        DVMTaskInterface.write_output("Error: " + str(e), args.output)

