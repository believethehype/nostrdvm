import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import Keys

from nostr_dvm.subscription import Subscription
from nostr_dvm.tasks import content_discovery_currently_popular
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
    #admin_config.DELETE_NIP89 = True
    #admin_config.PRIVKEY = ""
    #admin_config.EVENTID = ""

    discovery_test_sub = content_discovery_currently_popular.build_example_subscription("Currently Popular Notes DVM (with Subscriptions)", "discovery_content_test", admin_config)
    discovery_test_sub.run()

    #discovery_test = content_discovery_currently_popular.build_example("Currently Popular Notes DVM",
    #                                                                   "discovery_content_test", admin_config)
    #discovery_test.run()

    subscription_config = DVMConfig()
    subscription_config.PRIVATE_KEY = check_and_set_private_key("dvm_subscription")
    npub = Keys.parse(subscription_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys("dvm_subscription", npub)
    subscription_config.LNBITS_INVOICE_KEY = invoice_key
    subscription_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    subscription_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    sub_admin_config = AdminConfig()
    #sub_admin_config.USERNPUBS = ["7782f93c5762538e1f7ccc5af83cd8018a528b9cd965048386ca1b75335f24c6"] #Add npubs of services that can contact the subscription handler
    x = threading.Thread(target=Subscription, args=(Subscription(subscription_config, sub_admin_config),))
    x.start()

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
