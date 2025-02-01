import asyncio
import json

from nostr_sdk import NostrSigner, Keys, Client, Alphabet, SingleLetterTag, Filter, \
    PublicKey, init_logger, LogLevel, Tag

from nostr_dvm.utils.definitions import relay_timeout_long
from nostr_dvm.utils.nostr_utils import check_and_set_private_key


async def main():
    init_logger(LogLevel.DEBUG)
    options = {
        "max_results": 200,
        "relay": "wss://gleasonator.dev/relay"
    }

    keys = Keys.parse(check_and_set_private_key("test_client"))
    cli = Client(NostrSigner.keys(keys))

    await cli.add_relay(options["relay"])
    await cli.connect()

    ltags = ["#e", "pub.ditto.trends"]
    itags = [str(SingleLetterTag.lowercase(Alphabet.E))]
    authors = [PublicKey.parse("db0e60d10b9555a39050c258d460c5c461f6d18f467aa9f62de1a728b8a891a4")]
    notes_filter = Filter().authors(authors).custom_tags(SingleLetterTag.lowercase(Alphabet.L), ltags)

    events_struct = await cli.fetch_events(notes_filter, relay_timeout_long)
    events = events_struct.to_vec()


    result_list = []
    if len(events) > 0:
        event = events[0]
        print(event)
        result_list = []
        for tag in event.tags().to_vec():
            print(tag.as_vec())
            if tag.as_vec()[0] == "e":

                e_tag = Tag.parse(["e", tag.as_vec()[1], tag.as_vec()[2]])
                result_list.append(e_tag.as_vec())

    else:
        print("Nothing found")
        # for event in events:
        #    e_tag = Tag.parse(["e", event.id().to_hex()])
        return ""

    await cli.shutdown()
    print(json.dumps(result_list))
    return json.dumps(result_list)


asyncio.run(main())
