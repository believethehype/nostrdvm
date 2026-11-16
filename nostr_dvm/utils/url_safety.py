"""URL safety helpers shared by anything that fetches remote resources.

Job request events are attacker-controlled input. A `relays` tag or an `i`
tag can point at loopback, RFC1918 or link-local addresses to probe the
host's internal network (SSRF) — e.g. DVMs that fetch arbitrary URLs were
sent `http://127.0.0.1:8332/` (Bitcoin Core's RPC port) by probing events.
Reject those before any fetch or connection attempt.
"""
import ipaddress
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {"localhost"}

# Networks a job must never make us connect to.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),     # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),    # RFC1918
    ipaddress.ip_network("169.254.0.0/16"),    # link-local (cloud metadata)
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped (checked unwrapped below)
]


def is_public_url(url: str) -> bool:
    """True if the URL is http(s) and does not target a private network."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return True  # regular DNS name; resolution happens at fetch time
    # Unwrap IPv4-mapped IPv6 (::ffff:a.b.c.d) so mapped private nets are caught.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return not any(ip in net for net in _BLOCKED_NETWORKS)


def filter_public_urls(urls):
    """Split a list of URLs into (public, blocked) so callers can log rejections."""
    public, blocked = [], []
    for url in urls:
        (public if is_public_url(url) else blocked).append(url)
    return public, blocked


def is_valid_relay_url(url: str) -> bool:
    """True if the value looks like a connectable websocket relay URL.

    Request events can carry garbage in their `relays` tags (plain http URLs,
    host:port pairs, internal addresses). Connecting to each and waiting for
    the relay timeout stalls event delivery, so filter before use.
    """
    if not isinstance(url, str):
        return False
    if not (url.startswith("wss://") or url.startswith("ws://")):
        return False
    return is_public_url(url.replace("wss://", "https://", 1).replace("ws://", "http://", 1))
