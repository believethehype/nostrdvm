import json
from datetime import timedelta
from pathlib import Path

import dotenv
from duck_chat import ModelType
from nostr_sdk import Kind, Filter, PublicKey, SecretKey, Keys, NostrSigner, RelayLimits, Options, Client, Tag, \
    LogLevel, Timestamp, NostrDatabase

from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils import definitions
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import send_job_status_reaction


def playground(announce=False):
    # admin_config_db_scheduler = AdminConfig()
    # options = {
    #     "db_name": "db/nostr_recent_notes.db",
    #     "db_since": 24 * 60 * 60,  # 48h since gmt,
    #     "personalized": False,
    #     "logger": False}
    # image = ""
    # about = "I just update the Database based on my schedule"
    # db_scheduler = build_db_scheduler("DB Scheduler",
    #                                   "db_scheduler",
    #                                   admin_config_db_scheduler, options,
    #                                   image=image,
    #                                   description=about,
    #                                   update_rate=global_update_rate,
    #                                   cost=0,
    #                                   update_db=True)
    # db_scheduler.run()

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
    dvm_config.FIX_COST = 10

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://i.nostr.build/I8fJo0n355cbNEbS.png", # "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I create a personalized feed based on topics you were writing about recently",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.KIND = Kind(kind)
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {
        "input": "How do you call a noisy ostrich?",
    }

    dvm = GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)

    async def process(request_form):
        since = 2 * 60 * 60
        options = dvm.set_options(request_form)
        sk = SecretKey.from_hex(dvm.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)

        relaylimits = RelayLimits.disable()

        opts = (
            Options().wait_for_send(False).send_timeout(timedelta(seconds=dvm.dvm_config.RELAY_TIMEOUT))).relay_limits(
            relaylimits)

        cli = Client.with_opts(signer, opts)
        for relay in dvm.dvm_config.RELAY_LIST:
            await cli.add_relay(relay)
        # ropts = RelayOptions().ping(False)
        # await cli.add_relay_with_opts("wss://nostr.band", ropts)

        await cli.connect()
        #pip install -U https://github.com/mrgick/duckduckgo-chat-ai/archive/master.zip
        author = PublicKey.parse(options["user"])
        filterauth = Filter().kind(definitions.EventDefinitions.KIND_NOTE).author(author).limit(100)

        evts = await cli.get_events_of([filterauth], timedelta(5))

        text = ""
        for event in evts:
            text = text + event.content() + ";"

        text = text[:6000]

        prompt = "Only reply with the result. Here is a list of notes, seperated by ;. Find the 20 most important keywords and return them by a comma seperated list: " + text

        from duck_chat import DuckChat
        options = dvm.set_options(request_form)
        async with DuckChat(model=ModelType.GPT4o) as chat:
            query =  prompt
            result = await chat.ask_question(query)
            result = result.replace(", ", ",")
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

        database = await NostrDatabase.sqlite("db/nostr_recent_notes.db")

        timestamp_since = Timestamp.now().as_secs() -   since
        since = Timestamp.from_secs(timestamp_since)

        filter1 = Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(since)

        events = await database.query([filter1])
        if dvm.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + dvm.dvm_config.NIP89.NAME + "] Considering " + str(len(events)) + " Events")
        ns.finallist = {}
        search_list = result.split(',')

        for event in events:
            #if all(ele in event.content().lower() for ele in []):
            if any(ele in event.content().lower() for ele in search_list):
                    #if not any(ele in event.content().lower() for ele in []):
                    filt = Filter().kinds(
                        [definitions.EventDefinitions.KIND_ZAP, definitions.EventDefinitions.KIND_REACTION,
                         definitions.EventDefinitions.KIND_REPOST,
                         definitions.EventDefinitions.KIND_NOTE]).event(event.id()).since(since)
                    reactions = await database.query([filt])
                    if len(reactions) >= 1:
                        ns.finallist[event.id().to_hex()] = len(reactions)

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
    dvm.run(True)


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

    playground(announce=False)
