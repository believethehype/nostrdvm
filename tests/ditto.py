import asyncio
from datetime import timedelta

from nostr_sdk import Options, SecretKey, NostrSigner, Keys, Client, RelayOptions, Alphabet, SingleLetterTag, Filter, \
    Kind, PublicKey, init_logger, LogLevel, Tag

from nostr_dvm.utils.nostr_utils import check_and_set_private_key


async def main():
    init_logger(LogLevel.DEBUG)
    options = {
        "max_results": 200,
        "relay": "wss://gleasonator.dev/relay"
    }

    opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=5)))
    keys = Keys.parse(check_and_set_private_key("test_client"))
    signer = NostrSigner.keys(keys)
    cli = Client.with_opts(signer, opts)

    ropts = RelayOptions().ping(False)
    await cli.add_relay_with_opts(options["relay"], ropts)

    await cli.connect()

    userkeys = []

    ltags = ["pub.ditto.trends"]
    authors = [PublicKey.parse("db0e60d10b9555a39050c258d460c5c461f6d18f467aa9f62de1a728b8a891a4")]
    notes_filter = Filter().kinds([Kind(1985)]).authors(authors).custom_tag(SingleLetterTag.uppercase(Alphabet.L),
                                                                            ltags).custom_tag(
        SingleLetterTag.uppercase(Alphabet.I), ["e"])

    events = await cli.get_events_of([notes_filter], timedelta(seconds=5))

    result_list = []
    if len(events) > 0:
        event = events[0]
        result_list = []
        for tag in event.tags():
            if tag.as_vec()[0] == "e":
                e_tag = Tag.parse(["e", tag.as_vec()[1], tag.as_vec()[2]])
                result_list.append(e_tag.as_vec())
                print(tag.as_vec())
    else:
        print("Nothing found")
        # for event in events:
        #    e_tag = Tag.parse(["e", event.id().to_hex()])
        #    result_list.append(e_tag.as_vec())

    await cli.shutdown()
    # return json.dumps(result_list)


asyncio.run(main())
