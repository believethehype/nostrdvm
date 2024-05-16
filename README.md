# NostrDVM: Nostr NIP90 Data Vending Machine Framework

This framework provides a way to easily build and/or run `Nostr NIP90 DVMs in Python`.

This project is currently under development and additional tasks and features are added along the way. 
This means the project is in alpha status, interfaces might still change/break at this stage.


## To get started:

Create a new venv by running `"python -m venv venv"`
  - Place .env file (based on .env_example) in main folder.
  - Create a `LNbits` account on an accessible instance of your choice, enter one account's id and admin key (this account will create other accounts for the dvms)
  - the framework will then automatically create keys, nip89 tags and zapable NIP57 `lightning addresses` for your dvms in this file.
  - Activate the venv by typing `".venv\Scripts\activate"` on Windows or `"source venv/bin/activate"` otherwise
  - pip install nostr-dvm
  - Run python3 main.py. (or check single examples in the example folder)

In each task component DVM examples are already prepared. Feel free to play along with the existing ones.
You can also add new tasks by using the interface, just like the existing tasks in the `tasks` folder.

A `bot` is running by default that lists and communicates with the `DVMs` added to it, 
so your DVMs can be controled via any regular social client as well. 

If LNBits is not used, make sure your DVM's nostr accounts have a valid lightning address.

A tutorial on how to add additional tasks, as well as the larger server backend will be added at a later stage. 
