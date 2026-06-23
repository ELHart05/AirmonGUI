"""
Authentication for the privileged API.

Every state-changing or root-capable endpoint depends on `require_token`, which
checks the `X-Auth-Token` header against the configured token in constant time.
The only routes left open are the health check and the interactive docs.
"""

import hmac

from fastapi import Header, HTTPException, Request, status

from .config import AUTH_ENABLED, AUTH_TOKEN, CORS_ORIGINS


def require_token(
    request: Request, x_auth_token: str | None = Header(default=None)
) -> None:
    """FastAPI dependency guarding the privileged API.

    With auth enabled, a valid token is required. With auth disabled there is no
    token, but a cross-origin browser request is still rejected so a page the user
    is visiting cannot drive the tools (CSRF). Non-browser clients send no Origin
    and pass — that is the local CLI/automation path.
    """
    if not AUTH_ENABLED:
        origin = request.headers.get("origin")
        if origin is not None and origin not in CORS_ORIGINS:
            raise HTTPException(status_code=403, detail="Origin not allowed")
        return
    if not x_auth_token or not hmac.compare_digest(x_auth_token, AUTH_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API token",
            headers={"WWW-Authenticate": "Token"},
        )
