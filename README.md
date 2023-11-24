# NostrAI: Nostr NIP90 Data Vending Machine Framework

This framework provides a way to easily build and/or run `Nostr NIP90 DVMs in Python`.

This project is currently under development and additional tasks and features are added along the way. 
This means the project is in alpha status, interfaces might still change/break at this stage.


## To get started:
(Tested on Python 3.10)

Create a new venv by running `"python -m venv venv"`
  - Place .env file (based on .env_example) in main folder.
  - Set your own private hex keys, create NIP89 dtags on vendata.io, 
  - Install requirements.txt
  - Run python main.py.

In `playground.py` some DVMs are already prepared. Feel free to play along with the existing ones.
You can also add new tasks by using the interface, just like the existing tasks in the `tasks` folder.

A `bot` is running by default that lists and communicates with the `DVMs` added to it, 
so your DVMs can be controled via any regular client as well. 

The Framework optionally supports `LNbits` to create invoices instead of using a `lightning address`. If LNBits is not used, 
make sure your nostr accounts have a valid lightning address.


A tutorial on how to add additional tasks, as well as the larger server backend will be added at a later stage. 
