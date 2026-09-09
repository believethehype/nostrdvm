import json
import os
from datetime import timedelta

from nostr_sdk import (
    ClientBuilder, Filter, Keys, Kind, LogLevel, NostrLmdb, PublicKey, RelayUrl, SecretKey,
    SignerAuthenticator, Timestamp,
)

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils import definitions
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.discovery_utils import engagement_kinds, sync_discovery_database
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.engagement_profile_utils import (
    RANKING_PARAMS, affinity, apply_author_diversity, build_coengagement, credibility,
    event_action_weight, new_author_boost, note_engagement_base, oon_factor, profile_actions_by_author,
    recency_factor, score_note, top_level, ProfileCache)
from nostr_dvm.utils.nip88_utils import NIP88Config, check_and_set_d_tag_nip88, check_and_set_tiereventid_nip88
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag, create_amount_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events

"""
This File contains a Module to discover a personalized "For You" feed per requester,
inspired by the X For You algorithm: in-network (follows) + out-of-network (co-engagement)
candidates, weighted multi-action scoring, credibility, recency, diversity decay and
visibility filters.
Accepted Inputs: none (requester = param user, else the request author)
Outputs: A list of events
Params: max_results
"""


class DiscoverContentForYou(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "discover-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    request_form = None
    last_schedule: int
    db_since = 7 * 24 * 3600
    db_name = "db/nostr_foryou.db"
    profile_db_name = "db/nostr_profiles_foryou.db"
    history_days = 7
    profile_ttl_seconds = 3600
    personalized = True
    result = "[]"
    database = None
    profile_cache = None

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        self.database = dvm_config.DATABASE
        self.request_form = {"jobID": "generic"}
        opts = {"max_results": 200}
        self.request_form['options'] = json.dumps(opts)
        self.last_schedule = Timestamp.now().as_secs()
        if self.options.get("db_name"):
            self.db_name = self.options.get("db_name")
        if self.options.get("db_since"):
            self.db_since = int(self.options.get("db_since"))
        if self.options.get("history_days"):
            self.history_days = int(self.options.get("history_days"))
        if self.options.get("profile_ttl_seconds"):
            self.profile_ttl_seconds = int(self.options.get("profile_ttl_seconds"))
        self.profile_cache = ProfileCache(self.profile_db_name, self.dvm_config.SYNC_DB_RELAY_LIST,
                                          ttl_seconds=self.profile_ttl_seconds, history_days=self.history_days)
        if self.dvm_config.UPDATE_DATABASE:
            await self.sync_db()

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.to_vec()[0] == 'i':
                if tag.to_vec()[2] != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config
        request_form = {"jobID": event.id().to_hex(), "requester": event.author().to_hex()}
        max_results = 200
        user = None
        for tag in event.tags():
            vec = tag.to_vec()
            if vec[0] == 'i':
                pass
            elif vec[0] == 'param':
                if vec[1] == "max_results":
                    max_results = int(vec[2])
                elif vec[1] == "user":
                    user = vec[2]
        options = {"max_results": max_results}
        if user:
            options["user"] = user
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        return await self.calculate_result(request_form)

    def _resolve_user(self, request_form):
        options = self.set_options(request_form)
        user = options.get("user") or request_form.get("requester")
        if user:
            try:
                user = PublicKey.parse(user).to_hex()
            except Exception:
                user = None
        return user, int(options.get("max_results", 200))

    async def calculate_result(self, request_form):
        user, max_results = self._resolve_user(request_form)
        database = await NostrLmdb.open(self.db_name)
        try:
            return await self._personalized(database, user, max_results)
        except Exception as error:
            print("[" + self.dvm_config.NIP89.NAME + "] Personalized ranking failed, "
                  "falling back to global ranking: " + str(error))
            return await self._global_fallback(database, max_results)

    async def _personalized(self, database, user, max_results):
        now_secs = Timestamp.now().as_secs()
        candidate_since_secs = now_secs - RANKING_PARAMS["candidate_age_hours"] * 3600
        candidate_since = Timestamp.from_secs(candidate_since_secs)
        graph_since = Timestamp.from_secs(now_secs - self.db_since)

        notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(candidate_since))
        # map note ids to authors across the whole graph window so co-engagement can
        # credit engagement with liked authors whose notes are older than the candidate window
        graph_notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(graph_since))
        note_author_by_id = {note.id().to_hex(): note.author().to_hex() for note in graph_notes}

        context = await self.profile_cache.get_requester_context(user, note_author_by_id)
        follows = context["follows"]
        muted = context["muted"]
        keywords = context["keywords"]
        actions_by_author = context["actions_by_author"]
        liked_authors = context["liked_authors"]

        engagement = await database.query(
            Filter().kinds(engagement_kinds()).since(graph_since))

        # group engagement by tagged note id; compute per-author distinct engagers + totals.
        # an event tagging the same note via multiple tags (e.g. NIP-10 root+reply pointing
        # at the same id) counts once for that note
        engagement_by_note = {}
        engagers_by_author = {}
        total_by_author = {}
        seen = set()
        for event in engagement:
            weight = event_action_weight(event)
            engager = event.author().to_hex()
            event_id = event.id().to_hex()
            for tag in event.tags():
                vec = tag.to_vec()
                if vec[0] in ("e", "E") and len(vec) > 1 and vec[1] in note_author_by_id:
                    if (event_id, vec[1]) in seen:
                        continue
                    seen.add((event_id, vec[1]))
                    author = note_author_by_id[vec[1]]
                    engagement_by_note.setdefault(vec[1], []).append(event)
                    engagers_by_author.setdefault(author, set()).add(engager)
                    total_by_author[author] = total_by_author.get(author, 0.0) + weight

        exclude_self = getattr(self.dvm_config, "EXCLUDE_SELF_ENGAGEMENT", True)

        def passes_filters(note) -> bool:
            author = note.author().to_hex()
            if author == user or author in muted:
                return False
            content = note.content().lower()
            if any(keyword in content for keyword in keywords):
                return False
            return True

        def note_score(note) -> float:
            author = note.author().to_hex()
            base = note_engagement_base(engagement_by_note.get(note.id().to_hex(), []),
                                        author, exclude_self=exclude_self)
            return score_note(base,
                              affinity(author, actions_by_author),
                              credibility(len(engagers_by_author.get(author, set()))),
                              recency_factor(note.created_at().as_secs(), now_secs),
                              oon_factor(author, follows),
                              new_author_boost(total_by_author.get(author, 0.0)))

        in_network = [note for note in notes
                      if note.author().to_hex() in follows and passes_filters(note) and top_level(note)]
        in_network.sort(key=lambda note: -note.created_at().as_secs())
        in_network = in_network[:RANKING_PARAMS["in_network_cap"]]

        author_weights = build_coengagement(engagement, note_author_by_id, user, liked_authors)
        oon_author_set = {author for author in author_weights
                          if author not in follows and author not in muted and author != user}
        oon = [note for note in notes
               if note.author().to_hex() in oon_author_set and passes_filters(note) and top_level(note)]
        oon.sort(key=lambda note: -(author_weights[note.author().to_hex()]
                                    * note_engagement_base(engagement_by_note.get(note.id().to_hex(), []),
                                                           note.author().to_hex(), exclude_self=exclude_self)))
        oon = oon[:RANKING_PARAMS["oon_cap"]]

        candidates = in_network + oon
        if not candidates:
            return await self._global_fallback(database, max_results)

        ranked = sorted([(note, note_score(note)) for note in candidates], key=lambda pair: -pair[1])
        selected = apply_author_diversity(ranked, max_results)
        return json.dumps([["e", event.id().to_hex()] for event, score in selected])

    async def _global_fallback(self, database, max_results):
        now_secs = Timestamp.now().as_secs()
        candidate_since = Timestamp.from_secs(now_secs - RANKING_PARAMS["candidate_age_hours"] * 3600)
        graph_since = Timestamp.from_secs(now_secs - self.db_since)
        notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(candidate_since))
        engagement = await database.query(Filter().kinds(engagement_kinds()).since(graph_since))
        engagement_by_note = {}
        seen = set()
        for event in engagement:
            event_id = event.id().to_hex()
            for tag in event.tags():
                vec = tag.to_vec()
                if vec[0] in ("e", "E") and len(vec) > 1:
                    if (event_id, vec[1]) in seen:
                        continue
                    seen.add((event_id, vec[1]))
                    engagement_by_note.setdefault(vec[1], []).append(event)
        exclude_self = getattr(self.dvm_config, "EXCLUDE_SELF_ENGAGEMENT", True)
        scored = []
        for note in notes:
            if not top_level(note):
                continue
            author = note.author().to_hex()
            scored.append((note, note_engagement_base(engagement_by_note.get(note.id().to_hex(), []),
                                                      author, exclude_self=exclude_self)))
        scored.sort(key=lambda pair: -pair[1])
        return json.dumps([["e", event.id().to_hex()] for event, score in scored[:max_results]])

    async def post_process(self, result, event):
        """Overwrite the interface function to return a social client readable format, if requested"""
        for tag in event.tags():
            if tag.to_vec()[0] == 'output':
                format = tag.to_vec()[1]
                if format == "text/plain":  # check for output type
                    result = post_process_list_to_events(result)

        # if not text/plain, don't post-process
        return result

    async def schedule(self, dvm_config):
        if dvm_config.SCHEDULE_UPDATES_SECONDS == 0:
            return 0
        if Timestamp.now().as_secs() >= self.last_schedule + dvm_config.SCHEDULE_UPDATES_SECONDS:
            if self.dvm_config.UPDATE_DATABASE:
                await self.sync_db()
            self.last_schedule = Timestamp.now().as_secs()
            return 1
        return 0

    async def sync_db(self):
        cli = None
        try:
            sk = SecretKey.parse(self.dvm_config.PRIVATE_KEY)
            keys = Keys.parse(sk.to_hex())
            if self.database is None:
                self.database = await init_db(self.db_name, print_filesize=False)
            database = self.database
            cli = ClientBuilder().authenticator(SignerAuthenticator(keys)).database(database).build()
            for relay in self.dvm_config.SYNC_DB_RELAY_LIST:
                await cli.add_relay(RelayUrl.parse(relay))
            await cli.connect(timedelta(seconds=15))
            since = Timestamp.from_secs(Timestamp.now().as_secs() - self.db_since)
            event_filter = Filter().kinds(engagement_kinds()).since(since)
            await sync_discovery_database(cli, event_filter, self.dvm_config.NIP89.NAME)
            await cli.database().delete_events(Filter().until(Timestamp.from_secs(
                Timestamp.now().as_secs() - self.db_since)))
        except Exception as e:
            print(e)
        finally:
            if cli is not None:
                await cli.shutdown()


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, options, cost=0, update_rate=600, processing_msg=None,
                  update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    image = "https://blossom.primal.net/7b900a794626f480822c55e6da03d636141e6ad1da593a5723971c18f6a4611e.jpg"
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show a personalized For You feed, ranked for you",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "personalized": True,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default 200)"
            },
            "user": {
                "required": False,
                "values": [],
                "description": "Pubkey to build the feed for (defaults to the requester)"
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return DiscoverContentForYou(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                 admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(DiscoverContentForYou)
