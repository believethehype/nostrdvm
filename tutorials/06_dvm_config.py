# We are continuing with the example, but here we will focus on the DVMconfig.
# The DVM config allows us to custimize many things our DVM is doing, and we will focus on some
# of the main aspects here. Out side of the comments we keep the code form the last tutorial.

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

    # Remember, with build_default_config(identifier) the framework will either create or load certain information
    # such as private nostr keys, wallet information, and d tags.
    dvm_config = build_default_config(identifier)

    # Specific to the generic_dvm we are using, we set the Kind in the config so the DVM knows
    # to which event kinds it should react too. Other DVMs have their kind defined, see the task folder for many examples
    kind = Kind(5050)
    dvm_config.KIND = kind


    # OK now let's look for some more things we can configure

    # USE_OWN_VENV: Default = False. If we set USE_OWN_VENV to True, the DVM will create an own python
    # virtual environment where it will install dependencies
    # For example see tasks/imagegeneration_openai_dalle.py where the dvm framework and an openai library are
    # installed in a seperate venv, so dependencies don't get messes up with the main environment.
    # If you don't have specific dependencies, you can just leave it on false.
    dvm_config.USE_OWN_VENV = False

    # If we don't want to offer our services for free we can define a fix cost and a per unit cost.
    # The FIX_COST will be a fixed amount the DVM is asking for its services
    # THE PER_UNIT_COST will ask for a dynamic amound based on the lenght of the text, audio/video file etc.
    # Both costs will be added up and requested for the user.
    # Only if the invoice gets paid (or if you dont use lnbits, the event gets zapped via your lightning address,
    # the processing will start. The amount is in Sats/Satoshis.
    dvm_config.FIX_COST = 0
    dvm_config.PER_UNIT_COST = 0

    # You can overwrite the default relay list (see utils/dvmconfig.py) with relays of your choice
    dvm_config.RELAY_LIST = ["wss://relay.damus.io", "wss://nostr.oxtr.dev"]

    # Some DVMs, especially content based ones or filter ones used NENGENTROPY reconciliation.
    # This basically means it syncronizes local databases with relays. Not all relays support that,
    # but if they do, you can select which ones should be used to sync to your local database.
    # This example doesn't use reconciliation, but you might want to take a look at tasks/content_discovery_currently.popular.py for example.

    dvm_config.SYNC_DB_RELAY_LIST = ["wss://relay.damus.io", "wss://nostr.oxtr.dev",
                               "wss://relay.nostr.net", "wss://relay.primal.net"]

    # related to that  dvm_config.UPDATE_DATABASE can be used to signal if the dvm should update it's own database at all.
    # For example you might want to use a DVM that schedule updating a database and some others that only read from that database,
    # without the need of doing the step by themselves. For those you can set UPDATE_DATABASE to False
    dvm_config.UPDATE_DATABASE = False

    # in a similar manner, you can set how often the schedule task (e.g. for updating databases) should be called.
    # The scheduler is optional and not all DVMs will use it, but if they do, you can tell how often they should.
    dvm_config.SCHEDULE_UPDATES_SECONDS = 600

    # You can overwrite the default processing message the user gets when the DVM starts a task.
    # This can either be string or a list of strings where the DVM randomly picks one message
    dvm_config.CUSTOM_PROCESSING_MESSAGE = ["Doing the work", "Processing.."]


    # You can also decide if the DVM should send any of these processing messages at all.
    # For example for an LLM you might want to send directly a reply instead of telling each time that you are processing.
    dvm_config.SEND_FEEDBACK_EVENTS = True



    # You can also provide a list of relays the DVM shouldn't even try to answer to, should users have these in their inbox relays.
    # The reason is, some relays might be paid, or use auth, and we might not able to write there, so we just avoid doing it.
    # In utils/output_utils.py is a list of relays that won't work, but there might be others, or you might want to define your own list,
    # so you can overwrite it here. Otherwise, defaults will be used.
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST

    # Finally some DVMs might support Web of Trust filtering.
    # You find an example in tasks/content_discovery_update_db_only.py
    # This DVM only updates a Database that other DVMS might use.
    # By applying WOT filtering, it won't even download events outside of the WOT
    # So set WOT Filtering to True in order to use it.
    dvm_config.WOT_FILTERING = False
    # add a list of NPUBs that should be used to build the graph. It can be you and/or some trustworthy people.
    dvm_config.WOT_BASED_ON_NPUBS = ["99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64",
                          "460c25e682fda7832b52d1f22d3d22b3176d972f60dcdc3212ed8c92ef85065c",
                          "3f770d65d3a764a9c5cb503ae123e62ec7598ad035d836e2a810f3877a745b24"
                          ]
    # define the depth of the wot graph to follow. Note that a depth  or 3 or higher will take much longer, so 2 seems to be a good default value.
    dvm_config.WOT_DEPTH = 2

    # The rest of the code is as previously


    options = {
        "some_option": "#RunDVM",
    }
    name = "My very first DVM"


    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce


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
