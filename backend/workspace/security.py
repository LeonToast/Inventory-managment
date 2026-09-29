import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, Header, HTTPException
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
SECRET_FILE = Path(__file__).resolve().parent.parent / ".jwt_secret"


def _load_secret() -> bytes:
    """Use JWT_SECRET if set, else a key file created once, so restarts keep sessions valid."""
    if configured := os.getenv("JWT_SECRET"):
        return configured.encode()
    try:
        if stored := SECRET_FILE.read_text().strip():
            return stored.encode()
    except OSError:
        pass
    generated = secrets.token_urlsafe(48)
    try:
        # "x" fails if another worker created the file first; then we read theirs.
        with SECRET_FILE.open("x") as file:
            file.write(generated)
    except FileExistsError:
        return SECRET_FILE.read_text().strip().encode()
    except OSError:
        pass  # Read-only filesystem: fall back to a per-process secret.
    return generated.encode()


JWT_SECRET = _load_secret()
TOKEN_LIFETIME_SECONDS = 8 * 60 * 60
ROLES = {"Medlem", "Admin"}


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sign(payload: str) -> str:
    return _b64encode(hmac.new(JWT_SECRET, payload.encode(), hashlib.sha256).digest())


def issue_token(email: str, role: str) -> str:
    claims = {"sub": email, "role": role, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    payload = _b64encode(json.dumps(claims).encode())
    return f"{payload}.{_sign(payload)}"


def require_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inloggning krävs")
    try:
        payload, provided_signature = authorization[7:].split(".", 1)
        if not hmac.compare_digest(provided_signature, _sign(payload)):
            raise ValueError("Invalid token signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if not isinstance(claims, dict) or claims.get("exp", 0) <= time.time():
            raise ValueError("Expired token")
    except (ValueError, TypeError, UnicodeError) as error:
        raise HTTPException(status_code=401, detail="Ogiltig eller utgången inloggning") from error
    if not claims.get("sub") or claims.get("role") not in ROLES:
        raise HTTPException(status_code=401, detail="Ogiltig inloggning")
    return claims


def require_admin(claims: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    if claims.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Endast administratörer har åtkomst")
    return claims
