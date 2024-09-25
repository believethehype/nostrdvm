# Welcome back, this time we don't use a notebook, but we run an actual Python Script.
# We use a GenericDVM kind to start with. Now what's this? We have many predefined tasks in the task folder, but
# the genericDVM gives you some control for simple manipulation without caring about the tasks. Important is that
# we set the Kind of the GenericDVM. In Line 28 you see that we give it Kind 5050 (Text generation).
# On https://www.data-vending-machines.org/ there's an overview on all current kinds.
# On https://github.com/nostr-protocol/data-vending-machines/ you can make a PR for your own kind, if you come up with one later.
# Check the run_dvm function for more explanations
import asyncio
import os
from pathlib import Path

import dotenv

from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_sdk import Kind, Keys
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config, DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.zap_utils import change_ln_address


def run_dvm(identifier):
    # You have seen this one before, we did this in tutorial 2. This function will either create or load. the parameters of our DVMConfig.
    # Make sure you replace the identifier down in the main function with the one you generated in tutorial 2, or we will create a new one here.
    dvm_config = build_default_config(identifier)
    # As we will use a GenericDVM we need to give it a kind. Here we use kind 5050 (Text Generation) as we want to reply with some simple text.
    # There is a bunch of predefined DVMs in tasks that already have a kind set, but as we use the genericDVM we have to manually set it here.
    dvm_config.KIND = Kind(5050)

    # We can set options that we can later use in our process function. They are stored in a simple JSON
    options = {
        "some_option": "#RunDVM",
    }
    # We give the DVM a human readable name
    name = "My very first DVM"
    # Next we initalize a GenericDVM with the name and the dvm_config and the options we just created, as well as
    # an empty AdminConfig() and NIP89Config(). We will check these out in later tutorials, so don't worry about them now.


    # We add an admin config. By configuring it we can perform certain tasks, for example on start of the DVM
    admin_config = AdminConfig()
    # We broadcast our NIP65 inbox relays so other clients know where to write to so we receive it
    admin_config.REBROADCAST_NIP65_RELAY_LIST = True

    dvm = GenericDVM(name=name, dvm_config=dvm_config, options=options,
                     nip89config=NIP89Config(), admin_config=admin_config)


    # Normally we would define the dvm interface as we do in the tasks folder (we will do it later in the tutorials as well,
    # but here is a small hack to quickly manipulate what our dvm will do.
    async def process(request_form):
        # First we always parse the options from our request_form, that is build internally in the create_request_from_nostr_event function.
        options = dvm.set_options(request_form)
        # We build our result we are giving back from some text
        result = "The result of the DVM is: "
        # and the option we defined above and handed over to our DVM (some_option)
        result += options["some_option"]
        print(result)
        # Then we simply return the result
        return result

    dvm.process = process  # now we simply overwrite our DVM's process function with the one we defined here.
    # and finally we run the DVM #RunDVM
    dvm.run()

    # When the DVM is running you should see a blue message with the name and the public key in bech32 and hex format.
    # For the next exercise, copy the Hex key, and let this DVM run, you will need it :)


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

    # Replace the identifier with the one from the last notebook, or a new dvmconfig will be stored
    identifier = "tutorial01"

    # psst, you can change your lightning address here:
    #asyncio.run(change_ln_address(identifier, "test",  DVMConfig(), True))

    run_dvm(identifier)
