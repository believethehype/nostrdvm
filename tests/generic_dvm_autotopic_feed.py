import asyncio
import json
from datetime import timedelta
from pathlib import Path

import dotenv
from duck_chat import ModelType
from nostr_sdk import Kind, Filter, PublicKey, SecretKey, Keys, NostrSigner, RelayLimits, Options, ClientBuilder, Tag, \
    LogLevel, Timestamp, NostrDatabase

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils import definitions
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import relay_timeout
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import send_job_status_reaction
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

RELAY_LIST = ["wss://relay.nostrdvm.com",
              "wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              #"wss://relay.nostr.net"
              ]

SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                      #"wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"]



def playground(announce=False):

    framework = DVMFramework()

    kind = 5300
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce


    name = "Your topics (beta)"
    identifier = "duckduckchat_llm"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)
    dvm_config.KIND = Kind(kind)  # Manually set the Kind Number (see data-vending-machines.org)
    dvm_config.CUSTOM_PROCESSING_MESSAGE = "Creating a personalized feed based on the topics you write about. This might take a moment."
    dvm_config.FIX_COST = 0
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST



    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://i.nostr.build/I8fJo0n355cbNEbS.png",
        "picture": "https://i.nostr.build/I8fJo0n355cbNEbS.png", # "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I create a personalized feed based on topics you were writing about recently",
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "personalized": True,
        "amount": "free",
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.KIND = Kind(kind)
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {
        "input": "How do you call a noisy ostrich?",
    }

    dvm = GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)


    async def process_request(options, prompt):
        result = ""
        try:
            # pip install -U https://github.com/mrgick/duckduckgo-chat-ai/archive/master.zip
            from duck_chat import DuckChat
            async with DuckChat(model=ModelType.GPT4o) as chat:
                query = prompt
                result = await chat.ask_question(query)
                result = result.replace(", ", ",")
                print(result)
        except Exception as e:
            print(e)
        return result

    async def process(request_form):
        since = 2 * 60 * 60
        options = dvm.set_options(request_form)
        sk = SecretKey.parse(dvm.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        relaylimits = RelayLimits.disable()

        opts = Options().relay_limits(relaylimits)
        signer = NostrSigner.keys(keys)
        cli = ClientBuilder().signer(signer).opts(opts).build()
        for relay in dvm.dvm_config.RELAY_LIST:
            await cli.add_relay(relay)
        # ropts = RelayOptions().ping(False)
        # await cli.add_relay_with_opts("wss://nostr.band", ropts)

        await cli.connect()
        #pip install -U https://github.com/mrgick/duckduckgo-chat-ai/archive/master.zip
        author = PublicKey.parse(options["request_event_author"])
        print(options["request_event_author"])
        filterauth = Filter().kind(definitions.EventDefinitions.KIND_NOTE).author(author).limit(100)

        event_struct = await cli.fetch_events([filterauth], relay_timeout)
        text = ""

        if len(event_struct.to_vec()) == 0:
            #raise Exception("No Notes found")
            print("No Notes found")
            return json.dumps([])

        for event in event_struct.to_vec():
            text = text + event.content() + ";"


        text = text[:6000]

        prompt = "Only reply with the result. Here is a list of notes, seperated by ;. Find the 20 most important keywords and return them by a comma seperated list: " + text

        #loop = asyncio.get_running_loop()
        result =  await process_request(options, prompt)
        print(result)
        content = "I identified these as your topics:\n\n"+result.replace(",", ", ") + "\n\nProcessing, just a few more seconds..."
        await send_job_status_reaction(original_event_id_hex=dvm.options["request_event_id"], original_event_author_hex=dvm.options["request_event_author"],  client=cli, dvm_config=dvm_config, content=content)


        #prompt = "Only reply with the result. For each word in this comma seperated list, add 3 synonyms to the list. Return one single list seperated with commas.: " + result
        #async with DuckChat(model=ModelType.GPT4o) as chat:
        #    query = prompt
        #    result = await chat.ask_question(query)
        #    result = result.replace(", ", ",")
        #    print(result)

        from types import SimpleNamespace
        ns = SimpleNamespace()

        database = NostrDatabase.lmdb("db/nostr_recent_notes.db")

        timestamp_since = Timestamp.now().as_secs() -   since
        since = Timestamp.from_secs(timestamp_since)

        keywords = result.split(",")
        if len(keywords) == 0:
            return json.dumps([])

        filters = []
        for keyword in keywords:
            print(keyword)
            filters.append(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(since).search(" " + keyword + " "))

        events = await database.query(filters)
        if dvm.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + dvm.dvm_config.NIP89.NAME + "] Considering " + str(len(events.to_vec())) + " Events")
        ns.finallist = {}
        #search_list = result.split(',')

        for event in events.to_vec():
            #if all(ele in event.content().lower() for ele in []):
                    #if not any(ele in event.content().lower() for ele in []):
            filt = Filter().kinds(
                [definitions.EventDefinitions.KIND_ZAP, definitions.EventDefinitions.KIND_REACTION,
                 definitions.EventDefinitions.KIND_REPOST,
                 definitions.EventDefinitions.KIND_NOTE]).event(event.id()).since(since)
            reactions = await database.query([filt])
            if len(reactions.to_vec()) >= 1:
                ns.finallist[event.id().to_hex()] = len(reactions.to_vec())

        result_list = []
        finallist_sorted = sorted(ns.finallist.items(), key=lambda x: x[1], reverse=True)[:int(200)]
        for entry in finallist_sorted:
            # print(EventId.parse(entry[0]).to_bech32() + "/" + EventId.parse(entry[0]).to_hex() + ": " + str(entry[1]))
            e_tag = Tag.parse(["e", entry[0]])
            result_list.append(e_tag.as_vec())
        if dvm.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + dvm.dvm_config.NIP89.NAME + "] Filtered " + str(
                len(result_list)) + " fitting events.")
        # await cli.shutdown()
        return json.dumps(result_list)


    dvm.process = process  # overwrite the process function with the above one
    framework.add(dvm)
    framework.run()


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

    playground(announce=True)
