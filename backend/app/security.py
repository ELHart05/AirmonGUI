"""
Authentication for the privileged API.

Every state-changing or root-capable endpoint depends on `require_token`, which
checks the `X-Auth-Token` header against the configured token in constant time.
The only routes left open are the health check and the interactive docs.
"""

import hmac

from fastapi import Header, HTTPException, status

from .config import AUTH_TOKEN


def require_token(x_auth_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency: reject the request unless a valid token is present."""
    if not x_auth_token or not hmac.compare_digest(x_auth_token, AUTH_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token",
            headers={"WWW-Authenticate": "Token"},
        )
