"""SSRF guard for the JD URL fetcher.

A user-supplied URL is the most dangerous input in this app: left unguarded it
lets someone make the server fetch internal addresses (cloud metadata at
169.254.169.254, localhost services, private ranges). We:
  - allow only http/https
  - resolve the host and reject if ANY resolved IP is private/loopback/etc.
  - refuse redirects (each hop could point back at a private IP)
  - time out and cap the response size
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

ALLOWED_SCHEMES = {"http", "https"}


class UnsafeUrlError(ValueError):
    pass


def _ip_is_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme not allowed: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("missing host")

    # Resolve every address the host maps to; block if any is internal.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:  # pragma: no cover - network dependent
        raise UnsafeUrlError(f"cannot resolve host: {host}") from exc

    for info in infos:
        ip = info[4][0]
        if _ip_is_blocked(ip):
            raise UnsafeUrlError(f"resolves to blocked address: {ip}")
    return url


def safe_fetch(url: str, *, timeout_s: float, max_bytes: int) -> str:
    """Validate then fetch, with redirects DISABLED and a hard size cap."""
    validate_url(url)
    with httpx.Client(follow_redirects=False, timeout=timeout_s) as client:
        resp = client.get(url, headers={"User-Agent": "job-app-generator/1.0"})
        if resp.is_redirect:
            raise UnsafeUrlError("redirects are not followed")
        resp.raise_for_status()
        data = resp.content[:max_bytes]
    return data.decode(resp.encoding or "utf-8", errors="replace")
