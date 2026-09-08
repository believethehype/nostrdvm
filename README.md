# NostrDVM: Nostr NIP90 Data Vending Machine Framework

This framework provides a way to easily build and/or run `Nostr NIP90 DVMs in Python`.

This project is currently under development and additional tasks and features are added along the way. 
This means the project is in alpha status, interfaces might still change/break at this stage.

## Getting started 

Create a new venv by running `"python -m venv venv"`
  - Place .env file (based on .env_example) in main folder.
  - If you want the framework to manage wallets and lnaddresses automatically for you, create a `LNbits` account on an accessible instance of your choice, enter one account's id and admin key (this account will create other accounts for the dvms). Otherwise leave the lnbits .env variables empty and update each of your DVM's profile with a lightning address of your choice or alternativly, make sure the DVM is free.
  - the framework will then automatically create keys, nip89 tags and if lnbits is used zapable NIP57 `lightning addresses` for your dvms in this file.
  - Activate the venv by typing `".venv\Scripts\activate"` on Windows or `"source venv/bin/activate"` otherwise
  - pip install nostr-dvm
  - Run python3 main.py. (or check single examples in the example folder)

In each task component DVM examples are already prepared. Feel free to play along with the existing ones.
You can also add new tasks by using the interface, just like the existing tasks in the `tasks` folder.

A `bot` is running by default that lists and communicates with the `DVMs` added to it, 
so your DVMs can be controled via any regular social client as well. 

If LNBits is not used, make sure your DVM's nostr accounts have a valid lightning address.

A tutorial on how to add additional tasks, as well as the larger server backend will be added at a later stage. 

## SDK version and upgrading

This checkout targets `nostr-sdk==0.45.1`. Older SDK releases are not supported.
When upgrading an existing checkout, install it into the Python environment used
to run your DVMs:

```bash
python -m pip install -e .
python -m pip check
```

For example, if your environment is named `final`, use `final/bin/python` instead
of `python`. Installing only the SDK does not update the framework's installed
package metadata. Existing per-task environments in `cache/venvs/` also need the
updated framework and SDK installed using their own Python interpreter.

The migration uses `ClientBuilder` and `SignerAuthenticator`, `ReqTarget` for
subscriptions and fetching, `EventBuilder.finalize(keys)` for signing, and
`await NostrLmdb.open(...)` for databases. Events, query results, and event tags
use Python lists; individual tags expose `to_vec()`. Notifications are consumed
through a stream. Tor examples require an external SOCKS proxy at
`127.0.0.1:9050`; the old embedded-Tor option is no longer used.

The framework registers a process-wide daemon event loop for UniFFI callbacks
before database initialization and DVM startup. This lets Rust worker threads
call the Python database/authentication interfaces even when individual DVMs
use different threads or short-lived `asyncio.run()` loops. Custom entry points
that bypass the framework should call
`nostr_dvm.utils.sdk_utils.ensure_sdk_callback_loop()` before starting SDK work;
do not register a temporary application loop with `uniffi_set_event_loop`.
SDK 0.45.1 uses its global loop override for both callbacks and ordinary async
calls. A narrowly scoped runtime adapter therefore prefers the caller's running
loop and uses the daemon loop only on threads without one. No installed SDK
files are modified; the adapter is covered by cross-thread database tests.

Run the offline SDK regression suite without contacting relays or wallets:

```bash
python -m unittest discover -s tests/unit -v
```

Other scripts under `tests/` are manual/integration clients and may contact live
services or publish events. Task files using `process_venv` are worker entry
points requiring `--request`, `--identifier`, and `--output`, not standalone
server launchers.

### Media and optional dependencies

Media conversion uses `ffmpegio`; install the `ffmpeg` and `ffprobe` executables
on the host. MoviePy is no longer required. The offline suite exercises MP4 and
GIF conversion when these executables are available.

For the optional OpenAI image task, upgrade the old SDK rather than downgrading
AnyIO used by MCP:

```bash
python -m pip install --upgrade -e '.[openai]'
python -m pip check
```

Cashu 0.16.5 requires Pydantic 1 and HTTPX below 0.26. The MCP client requires
Pydantic 2 and HTTPX 0.27 or newer, so these versions cannot share an environment.
Keep legacy Cashu-enabled DVMs in a separate environment from MCP; do not
downgrade the shared MCP environment to satisfy Cashu. Do not remove Cashu from
an existing deployment until you have confirmed its wallet features are unused.

To opt into a bounded, read-only relay smoke test:

```bash
NOSTR_TEST_RELAY=wss://nostr.mom python -m unittest discover -s tests/integration -v
```

This fetches and verifies public notes without publishing events or making
payments. It requires working DNS and relay access. Payment regression tests
use mocked wallets and HTTP responses; they do not prove settlement against a
live wallet.

## Discovery database troubleshooting

Reply-routing metadata lookups have a five-second budget each. Results are cached
per client for five minutes; empty or failed lookups are cached for 30 seconds.
Request logs include event IDs to distinguish polling from repeated deliveries.
During each WOT sync cycle, relays explicitly reporting `negentropy not supported`
are excluded from subsequent Negentropy batches and covered by regular fetching.
Timeouts remain retryable, and capability knowledge resets on the next cycle.

Discovery loads the repository-root `.env`, even when launched from `tests/`
or an IDE. Default DVM configuration and generated-key persistence use that same
file; existing process environment variables take precedence. LNbits wallet
reuse requires `LNBITS_INVOICE_KEY_<IDENTIFIER>` (uppercase identifier). Creating
a new wallet requires the global `LNBITS_ADMIN_KEY` and `LNBITS_HOST`; failed
creation no longer writes empty wallet credentials to `.env`.

Popularity feeds count kind 1 replies, kind 1111 comments, reactions, reposts,
and zaps. Kind 1111 comments match either the lowercase `e` parent or uppercase
`E` root reference, with duplicate event IDs counted only once and the same
time window applied to both. Feed candidates remain unchanged; comments are
engagement signals, not new top-level note candidates.

Currently popular uses `DVMConfig.DATABASE` when supplied, otherwise opens
`options["db_name"]`. With `UPDATE_DATABASE=False`, run a database scheduler
against that same database. Its retention window must cover every consuming
feed's `db_since` window. Empty windows now log the newest stored note timestamp;
an empty popular result is returned as `[]` rather than stale cached results.

The scheduler and standalone popular sync wait for relay connections and report
their progress. The scheduler builds WOT before connecting its sync client and
splits WOT authors into batches of at most 500, avoiding oversized relay requests.
An empty WOT does not silently disable author filtering. Failed batches prevent
pruning, while successful batches remain stored. Both sync paths report
relay failures and database counts. If Negentropy fails on every relay, they try
a regular event fetch with the same time/kind/author filter and persist the
results. This fallback may be truncated by relay limits; it is not a full sync.
They skip pruning if both methods fail and always close the sync client.
The discovery example and scheduler no longer automatically wipe oversized
databases before syncing. LMDB files do not shrink after pruning; reclaim disk
space through explicit maintenance with all database users stopped, rather than
discarding the cache before a potentially unsuccessful resync.

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
