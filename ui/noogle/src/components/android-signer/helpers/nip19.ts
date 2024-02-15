import { getPublicKey, nip19 } from "nostr-tools";
import { bech32 } from '@scure/base'

export const Bech32MaxSize = 5000
export function isHexKey(key?: string) {
  if (key?.toLowerCase()?.match(/^[0-9a-f]{64}$/)) return true;
  return false;
}
export function isHex(str?: string) {
  if (str?.match(/^[0-9a-f]+$/i)) return true;
  return false;
}

export function getPubkeyFromDecodeResult(result?: nip19.DecodeResult) {
  if (!result) return;
  switch (result.type) {
    case "naddr":
    case "nprofile":
      return result.data.pubkey;
    case "npub":
      return result.data;
    case "nsec":
      return getPublicKey(result.data);
  }
}

function encodeBech32<Prefix extends string>(prefix: Prefix, data: Uint8Array): `${Prefix}1${string}` {
  let words = bech32.toWords(data)
  return bech32.encode(prefix, words, Bech32MaxSize) as `${Prefix}1${string}`
}
export function encodeBytes<Prefix extends string>(prefix: Prefix, bytes: Uint8Array): `${Prefix}1${string}` {
  return encodeBech32(prefix, bytes)
}
