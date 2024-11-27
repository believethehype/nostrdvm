# This is an experimental feature, as the NIP has not been merged at the time of writing this.
# NIP60/61 support so called nutzaps, or in other words, if a user carries their wallet on Nostr
# They can use it to interact with DVMS. In this tutorial we will once again keep our simple example
# But will focus on what needs to be done in order to make it work.


# Important: In order to make this work you need to manually install the cashu library in your main environment.
# Also see https://github.com/cashubtc/nutshell
# Depending on your system you might need to install some further dependencies. Please see the readme in the above link.

import asyncio
import json
import os
from pathlib import Path

import dotenv
from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_sdk import Kind, Keys
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config, DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nut_wallet_utils import NutZapWallet
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST
from nostr_dvm.utils.zap_utils import change_ln_address

def run_dvm(identifier, announce):


    dvm_config = build_default_config(identifier)
    kind = Kind(5050)
    dvm_config.KIND = kind
    dvm_config.FIX_COST = 3

    # Once you installed cashu, the rest is pretty staight forward:

    # Enable Nutzaps in the config (by default its off, because of the cashu dependency)
    dvm_config.ENABLE_NUTZAP = True
    # Define a relay to update your balance
    dvm_config.NUTZAP_RELAYS = ["wss://relay.primal.net"]
    # Define one or more mints you would like to receive on.
    dvm_config.NUZAP_MINTS = ["https://mint.gwoq.com"]
    # If you want you can auto_melt cashu token to your lightning address once they pass a certain threshold.
    dvm_config.ENABLE_AUTO_MELT = False
    dvm_config.AUTO_MELT_AMOUNT = 1000
    # If you update your mints in NUTZAP_MINTS make sure to reannounce these.
    dvm_config.REANNOUNCE_MINTS = True




    options = {
        "some_option": "#RunDVM",
    }
    name = "My very first DVM"

    # We simplify the rest of the Code, but you can use what you learned on the dvm_config and admin_config tutorials.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce


    dvm = GenericDVM(name=name, dvm_config=dvm_config, options=options,
                     nip89config=NIP89Config(), admin_config=admin_config)

    async def process(request_form):
        options = dvm.set_options(request_form)
        result = "The result of the DVM is: "
        result += options["some_option"]
        print(result)
        return result

    dvm.process = process
    dvm.run(True)



if __name__ == '__main__':
    #We open the .env file we created before.
    env_path = Path('.env')
    if not env_path.is_file():
        with open('.env', 'w') as f:
            print("Writing new .env file")
            f.write('')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    #A unique identifier that will be used to store keys in your .env file as well as for your ln address.
    # (If its already used it will get some random letters to it)
    identifier = "tutorial01"
    announce = False
    # psst, you can change your lightning address here:
    #asyncio.run(change_ln_address(identifier, "test",  DVMConfig(), True))

    run_dvm(identifier, announce)
