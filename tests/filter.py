import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import Keys

from nostr_dvm.subscription import Subscription
from nostr_dvm.tasks import content_discovery_currently_popular, discovery_censor_wot, discovery_inactive_follows
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


def playground():
    # Generate an optional Admin Config, in this case, whenever we give our DVMs this config, they will (re)broadcast
    # their NIP89 announcement
    # You can create individual admins configs and hand them over when initializing the dvm,
    # for example to whilelist users or add to their balance.
    # If you use this global config, options will be set for all dvms that use it.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.UPDATE_PROFILE = False

    discovery_test_sub = discovery_censor_wot.build_example("Censorship", "discovery_censor", admin_config)
    discovery_test_sub.run()

    #discovery_test_sub = discovery_inactive_follows.build_example("Inactive Followings", "discovery_inactive", admin_config)
    #discovery_test_sub.run()



    #keep_alive()


if __name__ == '__main__':
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
    playground()
