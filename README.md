# NostrDVM: Nostr NIP90 Data Vending Machine Framework

This framework provides a way to easily build and/or run `Nostr NIP90 DVMs in Python`.

This project is currently under development and additional tasks and features are added along the way. 
This means the project is in alpha status, interfaces might still change/break at this stage.

## Getting started 

Create a new venv by running `"python -m venv venv"`
  - Place .env file (based on .env_example) in main folder.
  - If you want the framework to manage wallets and lnaddresses automatically for you, create a `LNbits` account on an accessible instance of your choice, enter one account's id and admin key (this account will create other accounts for the dvms). Otherwise leave the lnbits .env vatiables empty and update each of your DVM's profile with a lightning address of your choice or alternativly, make sure the DVM is free.
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

## Getting started with Docker

Create `.env` from the example provided by us `.env_example`

```bash
cp .env_example .env
```

and set the necessary environmental variables:

```bash
LNBITS_ADMIN_KEY = ""
LNBITS_WALLET_ID = ""
LNBITS_HOST = "https://demo.lnbits.com/"
NOSTDRESS_DOMAIN = "nostrdvm.com"
```

To get the Docker container up and running:

```sh
# in foreground
docker compose up --build

# in background
docker compose up --build -d
```

To update your container, do:

```sh
git pull

docker compose build --no-cache

# in foreground
docker compose up

# in background
docker compose up -d
```

This will build the Docker image and start the `nostrdvm` service as defined in the `docker-compose.yml` file. 

## License

This project is licensed under the MIT License.
