import { BunkerProfile } from "./nip46";

/**
 * Checks the availability of a NIP05 address on a given domain.
 *
 * @param nip05 - The NIP05 address to check.
 * @throws {Error} If the NIP05 address is invalid. e.g. not in the form `name@domain`.
 * @returns A promise that resolves to a boolean indicating the availability of the NIP05 address.
 */
export async function checkNip05Availability(nip05: string, localBunker?: BunkerProfile): Promise<boolean> {
    if (nip05.split("@").length !== 2) throw new Error("Invalid nip05");
    // Skip availability check if the nip05 is for the local bunker
    if (localBunker && nip05.split("@")[1] === localBunker.domain) return true;

    const [username, domain] = nip05.split("@");
    try {
        const response = await fetch(`https://${domain}/.well-known/nostr.json?name=${username}`);
        const json = await response.json();
        return json.names[username] === undefined ? true : false;
    } catch (error) {
        console.error(error);
        return false;
    }
}

/**
 * Validates a Bunker's NIP-05.
 *
 * @param nip05 - The NIP05 to validate.
 * @param pubkey - The public key to compare against.
 * @returns A promise that resolves to a boolean indicating whether the NIP05 is valid for the bunkers pubkey.
 * Will also return false for invalid nip05 format.
 */
export async function validateBunkerNip05(nip05: string, pubkey: string): Promise<boolean> {
    if (nip05.split("@").length !== 2) return false;

    const domain = nip05.split("@")[1];

    try {
        const response = await fetch(`https://${domain}/.well-known/nostr.json?name=_`);
        const json = await response.json();
        return json.names["_"] === pubkey;
    } catch (error) {
        console.error(error);
        return false;
    }
}

/**
 * Generates a unique request ID.
 *
 * @returns {string} The generated request ID.
 */
export function generateReqId(): string {
    return Math.random().toString(36).substring(7);
}
