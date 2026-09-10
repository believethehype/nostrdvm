import json
import os
import pickle
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
from nostr_dvm.utils.output_utils import post_process_list_to_events, send_job_status_reaction
from nostr_dvm.utils.engagement_profile_utils import (
    RANKING_PARAMS, affinity, apply_author_diversity, credibility,
    engager_authors_from_events, event_action_weight, new_author_boost,
    oon_factor, profile_actions_by_author, recency_factor, score_note, top_level,
    weights_from_engager_authors, ProfileCache)
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
    _engagement_index = None
    _engagement_index_built_at = 0
    index_ttl_seconds = 600  # rebuild the engagement index at most this often (matches the default sync rate)
    rotation_pool_size = 600  # the feed rotates through this many top-ranked notes per user cycle
    _status_client = None
    BLOCKED_NIP05_DOMAINS = {"nostrmag.com"}  # bot-farm author domains, excluded from the feed
    seen_ttl_seconds = 24 * 3600  # notes served to a user are excluded from their feed for this long
    _seen_served = None  # {user_hex: {note_id: served_secs}}, persisted to disk
    _seen_loaded = False
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
        if user:
            cold = not self.profile_cache.has_context(user)
            await self._send_processing_status(request_form, cold)
        try:
            return await self._personalized(database, user, max_results)
        except Exception as error:
            print("[" + self.dvm_config.NIP89.NAME + "] Personalized ranking failed, "
                  "falling back to global ranking: " + str(error))
            return await self._global_fallback(database, max_results, user)

    async def _get_status_client(self):
        if self._status_client is None:
            keys = Keys.parse(SecretKey.parse(self.dvm_config.PRIVATE_KEY).to_hex())
            self._status_client = ClientBuilder().authenticator(SignerAuthenticator(keys)).build()
            for relay in self.dvm_config.RELAY_LIST:
                await self._status_client.add_relay(RelayUrl.parse(relay))
            await self._status_client.connect(timedelta(seconds=10))
        return self._status_client

    async def _send_processing_status(self, request_form, cold):
        message = ("Building your graph, this might take a minute or two.." if cold
                   else "Updating your feed..")
        try:
            client = await self._get_status_client()
            await send_job_status_reaction(request_form.get("jobID"), request_form.get("requester"),
                                           client, self.dvm_config, content=message,
                                           status="processing")
        except Exception as e:
            print("[" + self.dvm_config.NIP89.NAME + "] Status send failed: " + str(e))

    def _select_rotation(self, user, ranked, max_results, now_secs):
        """Rotate unseen notes through the top-ranked pool; when the pool is consumed,
        start a new rotation from the top instead of serving worse notes."""
        if user is None:
            return apply_author_diversity(ranked, max_results)
        pool_size = max(self.rotation_pool_size, 2 * max_results)
        pool = ranked[:pool_size]
        served = self._get_seen(user, now_secs)
        unseen = [(note, score) for note, score in pool
                  if note.id().to_hex() not in served]
        if len(unseen) < max_results:
            # pool exhausted for this cycle: restart from the best notes
            served.clear()
            self._persist_seen()
            unseen = pool
        selected = apply_author_diversity(unseen, max_results)
        self._mark_served(user, [note.id().to_hex() for note, _ in selected], now_secs)
        return selected

    @property
    def _index_path(self) -> str:
        return self.db_name + ".index.pkl"

    @property
    def _seen_path(self) -> str:
        return self.db_name + ".seen.json"

    def _load_seen(self):
        if self._seen_loaded:
            return
        self._seen_loaded = True
        if self._seen_served is None:
            self._seen_served = {}
        try:
            with open(self._seen_path) as handle:
                data = json.load(handle)
            for user_hex, state in data.get("users", {}).items():
                self._seen_served.setdefault(user_hex, {}).update(state.get("notes", {}))
        except Exception:
            pass

    def _persist_seen(self):
        try:
            data = {"users": {user: {"notes": notes}
                              for user, notes in self._seen_served.items()}}
            tmp = self._seen_path + ".tmp"
            with open(tmp, "w") as handle:
                json.dump(data, handle)
            os.replace(tmp, self._seen_path)
        except Exception as e:
            print("[" + self.dvm_config.NIP89.NAME + "] Could not persist seen memory: " + str(e))

    def _save_index(self):
        try:
            tmp = self._index_path + ".tmp"
            with open(tmp, "wb") as handle:
                pickle.dump({"index": self._engagement_index,
                             "built_at": self._engagement_index_built_at}, handle)
            os.replace(tmp, self._index_path)
        except Exception as e:
            print("[" + self.dvm_config.NIP89.NAME + "] Could not persist the engagement index: " + str(e))

    def _load_index(self, now_secs: float) -> bool:
        try:
            with open(self._index_path, "rb") as handle:
                data = pickle.load(handle)
            built_at = data["built_at"]
            if now_secs - built_at >= 1800:
                return False  # too stale: rebuild fresh instead of merging across the gap
            self._engagement_index = data["index"]
            self._engagement_index_built_at = built_at
            return True
        except Exception:
            return False

    def _get_seen(self, user_hex: str, now_secs: float) -> dict:
        self._load_seen()
        if self._seen_served is None:
            self._seen_served = {}
        served = self._seen_served.setdefault(user_hex, {})
        for note_id, served_secs in list(served.items()):
            if now_secs - served_secs >= self.seen_ttl_seconds:
                del served[note_id]
        return served

    def _mark_served(self, user_hex: str, note_ids: list, now_secs: float):
        served = self._get_seen(user_hex, now_secs)
        for note_id in note_ids:
            served[note_id] = now_secs
        self._persist_seen()

    def _unseen(self, user_hex: str, notes: list, now_secs: float) -> list:
        served = self._get_seen(user_hex, now_secs)
        return [note for note in notes if note.id().to_hex() not in served]

    @staticmethod
    def _domain_allowed(domain: str) -> bool:
        domain = (domain or "").lower().strip()
        if not domain:
            return True
        for blocked in DiscoverContentForYou.BLOCKED_NIP05_DOMAINS:
            if domain == blocked or domain.endswith("." + blocked):
                return False
        return True

    async def _build_engagement_index(self, database, graph_since):
        """Precompute the per-note engagement groups and per-author aggregates shared by
        every request. Full build on startup; afterwards merged incrementally."""
        engagement = await database.query(
            Filter().kinds(engagement_kinds()).since(graph_since))
        graph_notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(graph_since))
        note_author_by_id = {note.id().to_hex(): note.author().to_hex() for note in graph_notes}
        indexed_event_ids = {event.id().to_hex() for event in engagement}

        # group engagement by tagged note id; compute per-author distinct engagers + totals.
        # an event tagging the same note via multiple tags (e.g. NIP-10 root+reply pointing
        # at the same id) counts once for that note; self-engagement is skipped here so
        # the full build and incremental merges stay consistent
        exclude_self = getattr(self.dvm_config, "EXCLUDE_SELF_ENGAGEMENT", True)
        weights_by_note = {}
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
                    if exclude_self and engager == author:
                        continue
                    weights_by_note[vec[1]] = weights_by_note.get(vec[1], 0.0) + weight
                    engagers_by_author.setdefault(author, set()).add(engager)
                    total_by_author[author] = total_by_author.get(author, 0.0) + weight

        engager_authors = engager_authors_from_events(engagement, note_author_by_id)
        return {"weights_by_note": weights_by_note,
                "engagers_by_author": engagers_by_author,
                "total_by_author": total_by_author,
                "engager_authors": engager_authors,
                "note_author_by_id": note_author_by_id,
                "indexed_event_ids": indexed_event_ids}

    async def _get_engagement_index(self, database, now_secs=None):
        if now_secs is None:
            now_secs = Timestamp.now().as_secs()
        if self._engagement_index is None and self._load_index(now_secs):
            print("[" + self.dvm_config.NIP89.NAME + "] Loaded the engagement index from disk")
        if self._engagement_index is None:
            graph_since = Timestamp.from_secs(now_secs - self.db_since)
            self._engagement_index = await self._build_engagement_index(database, graph_since)
            self._engagement_index_built_at = now_secs
            self._save_index()
        elif (now_secs - self._engagement_index_built_at) >= self.index_ttl_seconds:
            # incremental: merge only events newer than the last build (with overlap for
            # late arrivals) so a refresh never blocks request handling for ~90s
            merge_since = Timestamp.from_secs(self._engagement_index_built_at - 1800)
            await self._merge_engagement_index(database, merge_since, self._engagement_index)
            self._engagement_index_built_at = now_secs
            self._save_index()
        return self._engagement_index

    async def _merge_engagement_index(self, database, merge_since, index):
        note_author_by_id = index["note_author_by_id"]
        weights_by_note = index["weights_by_note"]
        engagers_by_author = index["engagers_by_author"]
        total_by_author = index["total_by_author"]
        indexed_event_ids = index["indexed_event_ids"]

        engagement = await database.query(
            Filter().kinds(engagement_kinds()).since(merge_since))
        graph_notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(merge_since))
        for note in graph_notes:
            note_author_by_id[note.id().to_hex()] = note.author().to_hex()

        fresh = [event for event in engagement
                 if event.id().to_hex() not in indexed_event_ids]
        exclude_self = getattr(self.dvm_config, "EXCLUDE_SELF_ENGAGEMENT", True)
        for event in fresh:
            event_id = event.id().to_hex()
            indexed_event_ids.add(event_id)
            weight = event_action_weight(event)
            engager = event.author().to_hex()
            seen_notes = set()
            for tag in event.tags():
                vec = tag.to_vec()
                if vec[0] in ("e", "E") and len(vec) > 1 and vec[1] in note_author_by_id:
                    note_id = vec[1]
                    if note_id in seen_notes:
                        continue
                    seen_notes.add(note_id)
                    author = note_author_by_id[note_id]
                    if exclude_self and engager == author:
                        continue
                    weights_by_note[note_id] = weights_by_note.get(note_id, 0.0) + weight
                    engagers_by_author.setdefault(author, set()).add(engager)
                    total_by_author[author] = total_by_author.get(author, 0.0) + weight
        merged_engager_authors = engager_authors_from_events(fresh, note_author_by_id)
        for engager, authors in merged_engager_authors.items():
            index["engager_authors"].setdefault(engager, set()).update(authors)

    async def _personalized(self, database, user, max_results):
        now_secs = Timestamp.now().as_secs()
        candidate_since_secs = now_secs - RANKING_PARAMS["candidate_age_hours"] * 3600
        candidate_since = Timestamp.from_secs(candidate_since_secs)

        notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(candidate_since))

        index = await self._get_engagement_index(database)
        note_author_by_id = index["note_author_by_id"]
        weights_by_note = index["weights_by_note"]
        engagers_by_author = index["engagers_by_author"]
        total_by_author = index["total_by_author"]
        engager_authors = index["engager_authors"]

        context = await self.profile_cache.get_requester_context(user, note_author_by_id)
        follows = context["follows"]
        muted = context["muted"]
        keywords = context["keywords"]
        actions_by_author = context["actions_by_author"]
        liked_authors = context["liked_authors"]

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
            # self-engagement is already excluded when the index was built
            base = RANKING_PARAMS["base_floor"] + weights_by_note.get(note.id().to_hex(), 0.0)
            return score_note(base,
                              affinity(author, actions_by_author),
                              credibility(len(engagers_by_author.get(author, set()))),
                              recency_factor(note.created_at().as_secs(), now_secs),
                              oon_factor(author, follows),
                              new_author_boost(total_by_author.get(author, 0.0)))

        # over-fetch both pools (2x the caps): the NIP-05 blocklist filter then trims
        # them, and the rotation pool still fills to its full size afterwards
        in_network = [note for note in notes
                      if note.author().to_hex() in follows and passes_filters(note) and top_level(note)]
        in_network.sort(key=lambda note: -note.created_at().as_secs())
        in_network = in_network[:RANKING_PARAMS["in_network_cap"] * 2]

        author_weights = weights_from_engager_authors(engager_authors, user, liked_authors)
        oon_author_set = {author for author in author_weights
                          if author not in follows and author not in muted and author != user}
        oon = [note for note in notes
               if note.author().to_hex() in oon_author_set and passes_filters(note) and top_level(note)]
        oon.sort(key=lambda note: -(author_weights[note.author().to_hex()]
                                    * (RANKING_PARAMS["base_floor"]
                                       + weights_by_note.get(note.id().to_hex(), 0.0))))
        oon = oon[:RANKING_PARAMS["oon_cap"] * 2]

        pool_notes = in_network + oon
        domains = await self.profile_cache.get_author_domains(
            list({note.author().to_hex() for note in pool_notes}))
        pool_notes = [note for note in pool_notes
                      if self._domain_allowed(domains.get(note.author().to_hex(), ""))]
        in_network = [note for note in pool_notes
                      if note.author().to_hex() in follows][:RANKING_PARAMS["in_network_cap"]]
        oon = [note for note in pool_notes
               if note.author().to_hex() in oon_author_set][:RANKING_PARAMS["oon_cap"]]

        candidates = in_network + oon
        if not candidates:
            return await self._global_fallback(database, max_results, user)

        ranked = sorted([(note, note_score(note)) for note in candidates], key=lambda pair: -pair[1])
        selected = self._select_rotation(user, ranked, max_results, now_secs)
        return json.dumps([["e", event.id().to_hex()] for event, score in selected])

    async def _global_fallback(self, database, max_results, user=None):
        now_secs = Timestamp.now().as_secs()
        candidate_since = Timestamp.from_secs(now_secs - RANKING_PARAMS["candidate_age_hours"] * 3600)
        notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(candidate_since))
        index = await self._get_engagement_index(database)
        weights_by_note = index["weights_by_note"]
        scored = []
        for note in notes:
            if not top_level(note):
                continue
            scored.append((note, RANKING_PARAMS["base_floor"]
                           + weights_by_note.get(note.id().to_hex(), 0.0)))
        scored.sort(key=lambda pair: -pair[1])
        top = scored[:max(self.rotation_pool_size, max_results) * 2]
        if user:
            domains = await self.profile_cache.get_author_domains(
                list({note.author().to_hex() for note, _ in top}))
            top = [(note, score) for note, score in top
                   if self._domain_allowed(domains.get(note.author().to_hex(), ""))]
        selected = self._select_rotation(user, top, max_results, now_secs)
        return json.dumps([["e", event.id().to_hex()] for event, score in selected])

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
