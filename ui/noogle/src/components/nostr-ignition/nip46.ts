import { SimplePool } from "nostr-tools/pool";
import { generateSecretKey, getPublicKey, finalizeEvent, type Event, type UnsignedEvent } from "nostr-tools/pure";
import type { SubCloser, SubscribeManyParams, VerifiedEvent } from "nostr-tools";
import { encrypt, decrypt } from "nostr-tools/nip04";
import { NostrConnect, Handlerinformation } from "nostr-tools/kinds";
import { bytesToHex } from "@noble/hashes/utils";
import { EventEmitter } from "events";
import { validateBunkerNip05, generateReqId } from "./utils";

const DEFAULT_RELAYS = ["wss://relay.nostr.band", "wss://relay.nsecbunker.com"];
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const NPUB_REGEX = /^npub1[023456789acdefghjklmnpqrstuvwxyz]{58}$/;
export const PUBKEY_REGEX = /^[0-9a-z]{64}$/;

export type KeyPair = { privateKey: Uint8Array; publicKey: string };

export type Nip46Response = {
    id: string;
    result: string;
    error?: string;
    event: Event;
};

export type BunkerProfile = {
    pubkey: string;
    domain: string;
    nip05: string;
    name: string;
    picture: string;
    about: string;
    website: string;
    local: boolean;
};

// If you're running a local nsecbunker for testing you can add it here
// to have it show up in the list of available bunkers.
// The pubkey is the pubkey of the nsecbunker, not the localNostrPubkey
// The domain must be the domain configured in the nsecbunker.json file
// All other fields are optional

// eslint-disable-next-line prefer-const
let localBunker: BunkerProfile | undefined = undefined;

// Uncomment this block to add a local nsecbunker for testing
// localBunker = {
//     pubkey: "2ba00ed9b2108bf16de47fb3e2656bed051e314b1afa4dc04c213e67f41f28e1",
//     nip05: "",
//     domain: "really-trusted-oyster.ngrok-free.app",
//     name: "",
//     picture: "",
//     about: "",
//     website: "",
//     local: true,
// };

export class Nip46 extends EventEmitter {
    private pool: SimplePool;
    private subscription: SubCloser | undefined;
    private relays: string[];
    public keys: KeyPair | undefined;
    public remotePubkey: string | null;

    /**
     * Creates a new instance of the Nip46 class.
     * @param relays - An optional array of relay addresses.
     * @param remotePubkey - An optional remote public key. This is the key you want to sign as.
     * @param keys - An optional key pair.
     */
    public constructor(keys?: KeyPair, remotePubkey?: string, relays?: string[]) {
        super();

        this.pool = new SimplePool();
        this.relays = relays || DEFAULT_RELAYS;
        this.remotePubkey = remotePubkey || null;
        this.keys = keys || this.generateAndStoreKey();
        if (!this.subscription) this.subscribeToNostrConnectEvents();
    }

    /**
     * Generates a key pair, stores the keys in localStorage.
     *
     * @private
     * @returns {void}
     */
    private generateAndStoreKey(): KeyPair {
        const privateKey = generateSecretKey();
        const publicKey = getPublicKey(privateKey);
        // localNostrPubkey is the key that we use to publish events asking nsecbunkers for real signatures
        localStorage.setItem("localNostrPubkey", publicKey);
        localStorage.setItem("localNostrPrivkey", bytesToHex(privateKey));
        return { privateKey, publicKey };
    }

    /**
     * Subscribes to Nostr Connect events (kind 24133 and 24134) for the provided keys and relays.
     * It sets up a subscription to receive events and emit events for the received responses.
     *
     * @private
     * @returns {void}
     */
    private subscribeToNostrConnectEvents(): void {
        // Bail early if we don't have a local keypair
        if (!this.keys) return;

        // We do this alias because inside the onevent function, `this` is the event object
        // eslint-disable-next-line @typescript-eslint/no-this-alias
        // const nip46 = this;
        const parseResponseEvent = this.parseResponseEvent.bind(this);

        const subManyParams: SubscribeManyParams = {
            async onevent(event) {
                parseResponseEvent(event);
            },
            oneose() {
                console.log("EOSE received");
            },
        };

        this.subscription = this.pool.subscribeMany(
            this.relays,
            [{ kinds: [NostrConnect, 24134], "#p": [this.keys.publicKey] }],
            subManyParams
        );
    }

    /**
     * Fetches info on available signers (nsecbunkers) using NIP-89 events.
     *
     * @returns A promise that resolves to an array of available bunker objects.
     */
    async fetchBunkers(): Promise<BunkerProfile[]> {
        const events = await this.pool.querySync(this.relays, { kinds: [Handlerinformation] });
        // Filter for events that handle the connect event kind
        const filteredEvents = events.filter((event) =>
            event.tags.some((tag) => tag[0] === "k" && tag[1] === NostrConnect.toString())
        );

        // Validate bunkers by checking their NIP-05 and pubkey
        // Map to a more useful object
        const validatedBunkers = await Promise.all(
            filteredEvents.map(async (event) => {
                const content = JSON.parse(event.content);
                const valid = await validateBunkerNip05(content.nip05, event.pubkey);
                if (valid) {
                    return {
                        pubkey: event.pubkey,
                        nip05: content.nip05,
                        domain: content.nip05.split("@")[1],
                        name: content.name || content.display_name,
                        picture: content.picture,
                        about: content.about,
                        website: content.website,
                        local: false,
                    };
                }
            })
        );

        // Add local bunker if it exists
        if (localBunker) validatedBunkers.unshift(localBunker);

        return validatedBunkers.filter((bunker) => bunker !== undefined) as BunkerProfile[];
    }

    async sendRequest(id: string, method: string, params: string[], remotePubkey?: string): Promise<Nip46Response> {
        if (!this.keys) throw new Error("No keys found");
        const remotePk: string = (remotePubkey || this.remotePubkey) as string;
        if (!remotePk) throw new Error("No remote public key found");

        // Encrypt the content for the bunker (NIP-04)
        const encryptedContent = await encrypt(this.keys.privateKey, remotePk, JSON.stringify({ id, method, params }));

        // Create event to sign
        const verifiedEvent: VerifiedEvent = finalizeEvent(
            {
                kind: method === "create_account" ? 24134 : NostrConnect,
                tags: [["p", remotePk]],
                content: encryptedContent,
                created_at: Math.floor(Date.now() / 1000),
            },
            this.keys.privateKey
        );

        // Build auth_url handler
        const authHandler = (response: Nip46Response) => {
            if (response.result) {
                this.emit("authChallengeSuccess", response);
            } else {
                this.emit("authChallengeError", response.error);
            }
        };

        // Build the response handler
        const responsePromise = new Promise<Nip46Response>((resolve, reject) => {
            this.once(`response-${id}`, (response: Nip46Response) => {
                // Create account or auth challenge
                if (response.result === "auth_url") {
                    this.once(`response-${id}`, authHandler);
                    resolve(response);
                } else if (response.error) {
                    reject(response.error);
                } else {
                    resolve(response);
                }
            });
        });

        // Publish the event
        await Promise.any(this.pool.publish(this.relays, verifiedEvent));

        return responsePromise;
    }

    /**
     * Parses a response event and decrypts its content using the recipient's private key.
     *
     * @param event - The response event to parse.
     * @throws {Error} If no keys are found.
     * @returns An object containing the parsed response event data.
     */
    async parseResponseEvent(responseEvent: Event): Promise<Nip46Response> {
        if (!this.keys) throw new Error("No keys found");
        const decryptedContent = await decrypt(this.keys.privateKey, responseEvent.pubkey, responseEvent.content);
        const parsedContent = JSON.parse(decryptedContent);
        const { id, result, error, event } = parsedContent;
        this.emit(`response-${id}`, parsedContent as Nip46Response);
        return { id, result, error, event };
    }

    /**
     * Sends a ping request to the remote server.
     * Requires permission/access rights to bunker.
     * @throws {Error} If no keys are found or no remote public key is found.
     * @returns "Pong" if successful. The promise will reject if the response is not "pong".
     */
    async ping(): Promise<Nip46Response> {
        if (!this.keys) throw new Error("No keys found");
        if (!this.remotePubkey) throw new Error("No remote public key found");

        const reqId = generateReqId();
        const params: string[] = [];

        return this.sendRequest(reqId, "ping", params, this.remotePubkey);
    }

    /**
     * Connects to a remote server using the provided keys and remote public key.
     * Optionally, a secret can be provided for additional authentication.
     *
     * @param remotePubkey - Optional the remote public key to connect to.
     * @param secret - Optional secret for additional authentication.
     * @throws {Error} If no keys are found or no remote public key is found.
     * @returns "ack" if successful. The promise will reject if the response is not "ack".
     */
    async connect(remotePubkey?: string, secret?: string): Promise<Nip46Response> {
        if (!this.keys) throw new Error("No keys found");
        if (remotePubkey) this.remotePubkey = remotePubkey;
        if (!this.remotePubkey) throw new Error("No remote public key found");

        const reqId = generateReqId();
        const params: string[] = [this.keys.publicKey];
        if (secret) params.push(secret);

        return this.sendRequest(reqId, "connect", params, remotePubkey);
    }

    /**
     * Signs an event using the remote private key.
     * @param event - The event to sign.
     * @throws {Error} If no keys are found or no remote public key is found.
     * @returns A Promise that resolves to the signed event.
     */
    async sign_event(event: UnsignedEvent): Promise<Nip46Response> {
        if (!this.keys) throw new Error("No keys found");
        if (!this.remotePubkey) throw new Error("No remote public key found");

        const reqId = generateReqId();
        // Only param is the event to sign
        const params: string[] = [JSON.stringify(event)];

        return this.sendRequest(reqId, "sign_event", params, this.remotePubkey);
    }

    /**
     * Creates an account with the specified username, domain, and optional email.
     * @param bunkerPubkey - The public key of the bunker to use for the create_account call.
     * @param username - The username for the account.
     * @param domain - The domain for the account.
     * @param email - The optional email for the account.
     * @throws Error if no keys are found, no remote public key is found, or the email is present but invalid.
     * @returns A Promise that resolves to the auth_url that the client should follow to create an account.
     */
    async createAccount(
        bunkerPubkey: string,
        username: string,
        domain: string,
        email?: string
    ): Promise<Nip46Response> {
        if (!this.keys) throw new Error("No keys found");
        if (email && !EMAIL_REGEX.test(email)) throw new Error("Invalid email");

        const reqId = generateReqId();
        const params = [username, domain];
        if (email) params.push(email);

        return this.sendRequest(reqId, "create_account", params, bunkerPubkey);
    }
}
