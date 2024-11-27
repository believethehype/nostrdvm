# In tutorial 2 we have written a very simplistic DVM that replies with "The result of the DVM is: #RunDVM"
# In tutorial 3 we have written a client that requests a response from the DVM and gets the reply back.
# In this tutorial we build a simple bot that bridges the communication between the user and the Kind 5050
# (Text generation) DVM.
import threading
from pathlib import Path

import dotenv

from nostr_dvm.bot import Bot
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config

def run_dvm(identifier):

    bot_config = build_default_config(identifier)
    # The main purpose is of the Bot is to be an indexable overview of multiple DVMs. But we will use it in "chatbot" mode here
    # by setting the CHATBOT option to true
    bot_config.CHATBOT = True
    # And we simply hand over the publickey of our DVM from tutorial 1
    bot_config.DVM_KEY = "aa8ab5b774d47e7b29a985dd739cfdcccf93451678bf7977ba1b2e094ecd8b30" # TODO replace with your DVM

    # We update our relay list and profile and Start the bot
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP65_RELAY_LIST = True
    admin_config.UPDATE_PROFILE = True
    x = threading.Thread(target=Bot, args=([bot_config, admin_config]))
    x.start()

    # Now you can copy the npub to a Social client of your choice and (if tutorials 2 and 4 are running) it should reply
    # in your client.




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

    # A unique identifier that will be used to store keys in your .env file as well as for your ln address.
    # (If its already used it will get some random letters to it)
    identifier = "chat_bot"

    # psst, you can change your lightning address here:
    #asyncio.run(change_ln_address(identifier, "test",  DVMConfig(), True))

    run_dvm(identifier)
