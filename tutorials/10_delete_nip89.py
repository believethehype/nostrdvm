
# Welcome Back. So you were playing around with a DVM and announced it to the world, but now you rather would like
# to remove it, because you don't want to run it anymore or you did it by accident. In this tutorial we look at how to
# remove NIP89 announcements, so our DVM doesn't appear in clients anymore.
# Check the main function for more instructions.



import asyncio
from nostr_sdk import EventId, Keys, Client, NostrSigner

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import fetch_nip89_parameters_for_deletion

# Method to delete the NIP89, don't worry, you don't have to touch this, take a look in the main function.
async def delete_nip_89(event_id, private_key, relay_list, pow=True):
    event_id = EventId.parse(event_id).to_hex()
    keys = Keys.parse(private_key)
    dvm_config = DVMConfig()
    dvm_config.RELAY_LIST = relay_list
    
    
    client = Client(NostrSigner.keys(keys))
    for relay in dvm_config.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()
    
    await fetch_nip89_parameters_for_deletion(keys, event_id, client, dvm_config, pow)



if __name__ == '__main__':
    
    # What do you need to delete an event?
    
    # First, you need the event id of the announcement. You can copy the json of the announcement from various clients,
    # like Amethyst or you should also see it at noogle.lol/nip89. Copy the json to a text editor and in the first line
    # you should see an entry "id":"someid". Copy the id and enter it in the event_id field below:
    evend_id = "6f91dce309e....."
    
    # The second thing you need is the private key of the DVM the announcement was made for.
    # NostrDVM stores all your keys in the .env file. Open the .env file and search for 
    # DVM_PRIVATE_KEY_{IDENTIFIER_OF_YOUR_DVM}. Enter it below in the field private_key:
    
    private_key = "6221e3181....."
    
    # You can either use Proof of Work to send the delete event or not. Some relays require you to use POW in order to write.
    # Sending a POW event might take up to a couple of minutes, so if you decide to use it, have some patience in the progress.
    # If you know the relays you published your announcements to do not require POW, you can also set it to False which speeds up the progress.
    pow = True
    
    # And finally set the relay list you want to send the deletion request to. Ideally, you use the same relays that you use 
    # in your DVM's config. Maybe announcements also got propagated to other relays, so you might need to play around a bit until it's gone everywhere.
    RELAY_LIST = ["wss://relay.primal.net",
                  "wss://nostr.mom",
                  "wss://nostr.oxtr.dev",
                  ]
    
    # That's it. Once you entered the info, run the script and if your private key matches the ID and the event can be found it should be deleted. 
    # Otherwise you'll get a warning
    asyncio.run(delete_nip_89(evend_id, private_key, RELAY_LIST, pow))