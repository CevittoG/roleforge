"""Edge auth verification (defense-in-depth).

Cloudflare Access authenticates the user at the edge and forwards a signed JWT
in the `Cf-Access-Jwt-Assertion` header. We re-verify it here so the origin
rejects anything that didn't pass Access — even if the network-level origin
lock (Authenticated Origin Pulls / WAF) ever failed open.

We additionally require a shared secret header that Cloudflare injects, so a
direct hit on the *.onrender.com URL (bypassing Cloudflare entirely) is refused.
"""
from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.config import Settings, get_settings

_jwks_cache: dict[str, tuple[PyJWKClient, float]] = {}
_JWKS_TTL_S = 3600


def _jwks_client(team_domain: str) -> PyJWKClient:
    now = time.monotonic()
    cached = _jwks_cache.get(team_domain)
    if cached and (now - cached[1]) < _JWKS_TTL_S:
        return cached[0]
    client = PyJWKClient(f"https://{team_domain}/cdn-cgi/access/certs")
    _jwks_cache[team_domain] = (client, now)
    return client


def verify_access(
    cf_jwt: str | None = Header(default=None, alias="Cf-Access-Jwt-Assertion"),
    origin_secret: str | None = Header(default=None, alias="X-Origin-Secret"),
) -> dict[str, Any]:
    """FastAPI dependency. Raises 401/403 unless both checks pass."""
    settings: Settings = get_settings()

    # Local-dev escape hatch. The dependency stays wired on every /api route;
    # we just no-op the checks when the operator explicitly opted out via env.
    if not settings.auth_required:
        return {"sub": "local-dev", "email": "local@dev"}

    # 1) Origin lock: request must have come through Cloudflare.
    if not origin_secret or origin_secret != settings.origin_shared_secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "origin not permitted")

    # 2) Cloudflare Access JWT.
    if not cf_jwt:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing access token")

    try:
        signing_key = _jwks_client(settings.cf_access_team_domain).get_signing_key_from_jwt(cf_jwt)
        claims = jwt.decode(
            cf_jwt,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.cf_access_aud,
            issuer=f"https://{settings.cf_access_team_domain}",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access token") from exc

    return claims
