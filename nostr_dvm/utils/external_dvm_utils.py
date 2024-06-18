import asyncio
import json
from datetime import timedelta

from nostr_sdk import PublicKey, Options, Keys, Client, NostrSigner

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config, nip89_fetch_events_pubkey
from nostr_dvm.utils.output_utils import PostProcessFunctionType


async def build_client(config):
    opts = (Options().wait_for_send(True).send_timeout(timedelta(seconds=config.RELAY_TIMEOUT))
            .skip_disconnected_relays(True))
    keys = Keys.parse(config.PRIVATE_KEY)
    signer = NostrSigner.keys(keys)
    client = Client.with_opts(signer, opts)

    for relay in config.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()
    return client


def build_external_dvm(pubkey, task, kind, fix_cost, per_unit_cost, config,
                             external_post_process=PostProcessFunctionType.NONE):
    dvm_config = DVMConfig()
    dvm_config.PUBLIC_KEY = PublicKey.from_hex(pubkey).to_hex()
    dvm_config.FIX_COST = fix_cost
    dvm_config.PER_UNIT_COST = per_unit_cost
    dvm_config.EXTERNAL_POST_PROCESS_TYPE = external_post_process

    client = asyncio.run(build_client(config))

    nip89content_str = asyncio.run(nip89_fetch_events_pubkey(client, pubkey, kind))
    name = "External DVM"
    image = "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg"
    about = "An External DVM with no info"
    nip90params = {}
    encryption_supported = False
    cashu_accepted = False

    if nip89content_str is not None:
        print(nip89content_str)
        nip89content = json.loads(nip89content_str)
        if nip89content.get("name"):
            name = nip89content.get("name")
        if nip89content.get("image"):
            image = nip89content.get("image")
        if nip89content.get("about"):
            about = nip89content.get("about")
        if nip89content.get("nip90Params"):
            nip90params = nip89content["nip90Params"]
        if nip89content.get("encryptionSupported"):
            encryption_supported = nip89content["encryptionSupported"]
        if nip89content.get("cashuAccepted"):
            cashu_accepted = nip89content["cashuAccepted"]
    else:
        print("No NIP89 set for " + name)
    nip89info = {
        "name": name,
        "image": image,
        "about": about,
        "encryptionSupported": encryption_supported,
        "cashuAccepted": cashu_accepted,
        "nip90Params": nip90params
    }
    nip89config = NIP89Config()
    nip89config.KIND = kind
    nip89config.CONTENT = json.dumps(nip89info)

    interface = DVMTaskInterface(name=name, dvm_config=dvm_config, nip89config=nip89config, task=task)
    interface.SUPPORTS_ENCRYPTION = encryption_supported
    interface.ACCEPTS_CASHU = cashu_accepted

    return interface
