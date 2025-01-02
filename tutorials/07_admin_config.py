# Welcome back. This is a short tutorial to show us what the admin_config can do for us.
# We once again use our simple example (tutorial 02, 05 and 06) and focus on a particular thing,
# which this time is the admin_config. Jump straight to line 34.
import asyncio
import json
import os
from pathlib import Path

import dotenv

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_sdk import Kind, Keys
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config, DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST
from nostr_dvm.utils.zap_utils import change_ln_address

# We keep the main code structure almost the same as in tutorial02 and 05.
def run_dvm(identifier, announce):

    # Initialize the framework
    framework = DVMFramework()

    dvm_config = build_default_config(identifier)
    kind = Kind(5050)
    dvm_config.KIND = kind


    options = {
        "some_option": "#RunDVM",
    }
    name = "My very first DVM"

    # Here is the admin_config. We have used it before, for example in tutorial 05 for announcing the DVM with NIP89.
    # The admin_config is something the DVM does on start. For example, as we used it in tutorial 05
    # We tell our DVM that it should (re)announce the NIP89 on startup, as well as the NIP65 Relay list,
    # and update our profile as well with the Nip89 info.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    #The admin config allows some more things you can do, let's take a look at the most important ones.

    # For some tasks we want to do something with one or more npubs. We can define the npubs that are concerned in
    # admin_config.USERNPUBS
    admin_config.USERNPUBS = ["npub...", "123hex"]

    # For example we can whiteliste the Npubs in that list by setting
    admin_config.WHITELISTUSER = True
    # Whitelisting means that the DVM will not send an invoice to these users but will just start processing the task when requested.

    # We can also unwhitelist these users (or a subset of these users, or different users) at startup
    admin_config.UNWHITELISTUSER = True

    # We can also blacklist users. Service will be denied to blacklisted npubs.
    # For example if some npubs might spam or attack DVMs you can blacklist them there.
    admin_config.BLACKLISTUSER = True


    # You can delete information about the users in USERNPUBS. This way you can also unwhitelist them, or unblacklist them.
    # If they somehow have some balance with a DVM or Bot, it will also be removed.
    admin_config.DELETEUSER = False

    # This is a bit dangerous and shouldn't be used in 99% of cases, but you can wipe a DVMs internal database with:
    admin_config.ClEANDB = False #True, but we leave it on false here, just in case.

    # The following command gives us an overview on the contents of the DVMs database on startup:
    admin_config.LISTDATABASE = True


    # The following might come in handy:
    # If you want to withdraw the NIP89 announcement, you can delete it by setting:
    admin_config.DELETE_NIP89 = True
    # You also need to hand over the private keys (which are already stored in the dvm_config)
    admin_config.PRIVKEY = dvm_config.PRIVATE_KEY
    # And the event ID of the announcement. You can find this for example on noogle.lol/nip89 or on vendata.io or nostrudel.ninja,
    #by copying the json of the NIP89 announcement
    # Enter the EventID here (Hex or Bech32):
    admin_config.EVENTID = "ff28be59708ee597c7010fd43a7e649e1ab51da491266ca82a84177e0007e4d6"
    # Some relays require POW, so you can activate it here. It might still take a few attempts to delete and take a bit longer.
    # but in general it is recommended to do it for a higher chance of success.
    admin_config.POW = True


    # You can also announce the NIP88 or delete NIP88 (Subscription event status) similar to NIP89,
    # but we will introduce this in a later tutorial.

    # And that's it for this one. See you next time.



    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I'm a very simply DVM that always responds with the same message.",
        "supportsEncryption": True,
        "nip90Params": {
            "some_option": {
                "required": False,
                "values": []
            }
        }
    }

    # We now create or Nip89Config object
    nip89config = NIP89Config()
    nip89config.KIND = kind
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)


    dvm = GenericDVM(name=name, dvm_config=dvm_config, options=options,
                     nip89config=nip89config, admin_config=admin_config)

    async def process(request_form):
        options = dvm.set_options(request_form)
        result = "The result of the DVM is: "
        result += options["some_option"]
        print(result)
        return result

    dvm.process = process
    framework.add(dvm)

    framework.run()



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
