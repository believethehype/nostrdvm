import os
from pathlib import Path

import dotenv
from nostr_sdk import Keys

from nostr_dvm.tasks import content_discovery_test
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive


def playground():
    # Generate an optional Admin Config, in this case, whenever we give our DVMs this config, they will (re)broadcast
    # their NIP89 announcement
    # You can create individual admins configs and hand them over when initializing the dvm,
    # for example to whilelist users or add to their balance.
    # If you use this global config, options will be set for all dvms that use it.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.UPDATE_PROFILE = False

    discovery_test = content_discovery_test.build_example("Dicovery Test DVM", "discovery_content_test", admin_config)
    discovery_test.run()

    keep_alive()


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
