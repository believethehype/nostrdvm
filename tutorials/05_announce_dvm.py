# Let's have again a look at our main DVM from tutorial 02.
# All previous descriptions of what's happening has been removed, so refer to exercise02 to see whats going on.
# In this tutorial we want to focus on announcing our DVM so clients can find it.



import asyncio
import json
import os
from pathlib import Path

import dotenv
from sympy import false

from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_sdk import Kind, Keys
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config, DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.zap_utils import change_ln_address

# We keep the main code structure almost the same as in tutorial02.
def run_dvm(identifier, announce):
    dvm_config = build_default_config(identifier)
    kind = Kind(5050)
    dvm_config.KIND = kind
    options = {
        "some_option": "#RunDVM",
    }
    name = "My very first DVM"

    # First thing you'll notice we set the parameter REBROADCAST_NIP89. If we set announce to true when we call our function,
    # it will announce the DVM on Nostr, it is set to false by default here, so you don't accidently do it, but feel free to set it to true
    # once you're ready to try it, set it to True in the main function.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    # We can also update our regular Nostr profile based on the NIP89 info we will enter in a minute.
    admin_config.UPDATE_PROFILE = announce


    #What we do change tho is adding a Nip89Config.
    # Previously we just handed over an empty default config.
    # Now we adjust it a bit.

    # The main part is the nip89 info struct,
    # it includes a profile like announcement of what the DVM can do, including an image, a name and a description.
    # NostrDVM also supports encrypted requests so we add the flag encryptionSupported
    # so clients know we can receive encrypted requests.

    #nip90Params announces options that may or must be set (depending on the required flag)
    # They may contain a list of possible values or just be freetext

    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I'm a very simply DVM that always responds with the same message.",
        "encryptionSupported": True,
        "nip90Params": {
            "some_option": {
                "required": False,
                "values": []
            }
        }
    }

    # We now create or Nip89Config object
    nip89config = NIP89Config()
    # For generic_dvms only, we have to manually set the Kind to the NIP89 announcement,
    # predefined tasks already know their kind
    nip89config.KIND = kind
    # We set a d tag. We need the dtag so if we want to update or delete the announcement, relays know which event is meant
    # You can choose a dtag you like. Here we build a hash from identiier, name, key and image and store it in the .env file.
    # So even if you change the name or image, it will now use the dtag from the env file until you delete it.
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    # We dump the nip89info struct from above to the content
    nip89config.CONTENT = json.dumps(nip89info)


    # And we hand over the nip89config we just created instead of an empty one.
    # Notice, when we set the admin_config.REBROADCAST_NIP89 = True, the framework will announce your DVM to the world.
    # You can change parameters, and they will be updated next time you rebroadcast the nip89 announcement.




    dvm = GenericDVM(name=name, dvm_config=dvm_config, options=options,
                     nip89config=nip89config, admin_config=admin_config)

    async def process(request_form):
        options = dvm.set_options(request_form)
        result = "The result of the DVM is: "
        result += options["some_option"]
        print(result)
        return result

    dvm.process = process
    dvm.run()



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
