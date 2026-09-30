import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException
from pwdlib import PasswordHash

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

password_hash = PasswordHash.recommended()
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)
TOTP_ENCRYPTION_KEY = base64.urlsafe_b64encode(
    hmac.new(JWT_SECRET.encode(), b"smart-lagring-totp-encryption", hashlib.sha256).digest()
)


def encrypt_totp_secret(secret: str) -> str:
    from cryptography.fernet import Fernet

    return Fernet(TOTP_ENCRYPTION_KEY).encrypt(secret.encode()).decode("ascii")


def decrypt_totp_secret(encrypted_secret: str) -> str:
    from cryptography.fernet import Fernet, InvalidToken

    try:
        return Fernet(TOTP_ENCRYPTION_KEY).decrypt(encrypted_secret.encode()).decode("ascii")
    except (InvalidToken, UnicodeDecodeError) as error:
        raise ValueError("Stored two-factor secret cannot be decrypted") from error


def issue_token(email: str, role: str) -> str:
    encode = lambda value: base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
    payload = encode(json.dumps({"sub": email, "role": role, "exp": int(time.time()) + 28800}).encode())
    signature = encode(hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def require_authenticated(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Inloggning krävs")
    try:
        payload, provided_signature = authorization[7:].split(".", 1)
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode("ascii")
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise ValueError("Invalid token signature")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims.get("exp", 0) <= int(time.time()):
            raise ValueError("Expired token")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=401, detail="Ogiltig eller utgången inloggning") from error
    if claims.get("role") not in {"Admin", "Worker", "Medlem"}:
        raise HTTPException(status_code=403, detail="Ogiltig användarroll")
    return claims


def require_admin(authorization: str | None = Header(default=None)) -> dict[str, str]:
    claims = require_authenticated(authorization)
    if claims.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Endast administratörer har åtkomst")
    return claims
