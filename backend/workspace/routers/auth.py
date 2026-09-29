import hashlib
import hmac
import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..database import members_collection
from ..models import LoginCredentials
from ..security import issue_token, password_hash, require_user

router = APIRouter(tags=["authentication"])

LEGACY_SHA256 = re.compile(r"[0-9a-fA-F]{64}")
INVALID_LOGIN = "Fel e-postadress eller lösenord."


def _is_dev_admin(credentials: LoginCredentials) -> bool:
    """Optional local admin login, only enabled when DEV_ADMIN_EMAIL/DEV_ADMIN_PASSWORD are set."""
    email, password = os.getenv("DEV_ADMIN_EMAIL"), os.getenv("DEV_ADMIN_PASSWORD")
    if not email or not password:
        return False
    return hmac.compare_digest(credentials.email.encode(), email.encode()) and hmac.compare_digest(
        credentials.password.encode(), password.encode()
    )


def _session(name: str, email: str, role: str) -> dict[str, str]:
    return {"name": name, "email": email, "role": role, "access_token": issue_token(email, role)}


def _password_matches(members: Any, member: dict[str, Any], password: str) -> bool:
    """Check a password against the stored hash. A legacy SHA-256 hash is upgraded to Argon2
    once the password is correct."""
    stored_hash = member.get("password_hash", "")
    if stored_hash.startswith("$argon2"):
        try:
            return password_hash.verify(password, stored_hash)
        except (ValueError, TypeError):
            return False
    if not LEGACY_SHA256.fullmatch(stored_hash):
        return False
    legacy_hash = hashlib.sha256(password.encode()).hexdigest()
    if not hmac.compare_digest(legacy_hash, stored_hash.lower()):
        return False
    members.update_one(
        {"_id": member["_id"]}, {"$set": {"password_hash": password_hash.hash(password)}}
    )
    return True


@router.post("/login")
def login(credentials: LoginCredentials) -> dict[str, str]:
    if _is_dev_admin(credentials):
        return _session("Admin", credentials.email, "Admin")
    members = members_collection()
    member = members.find_one(
        {"email": {"$regex": "^" + re.escape(credentials.email.strip()) + "$", "$options": "i"}},
        {"name": 1, "email": 1, "role": 1, "password_hash": 1},
    )
    if not member or not _password_matches(members, member, credentials.password):
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)
    now = datetime.now(timezone.utc)
    members.update_one(
        {"_id": member["_id"]}, {"$set": {"last_login_at": now, "last_seen_at": now}}
    )
    return _session(member["name"], member["email"], member.get("role", "Medlem"))


@router.post("/heartbeat")
def heartbeat(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    # Lets the members list tell who is currently online. Matches nothing for the dev admin.
    members_collection().update_one(
        {"email": user["sub"]}, {"$set": {"last_seen_at": datetime.now(timezone.utc)}}
    )
    return {"status": "ok"}


@router.post("/logout")
def logout(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    # The built-in dev admin has no member document, so this simply matches nothing for it.
    members_collection().update_one(
        {"email": user["sub"]}, {"$set": {"last_logout_at": datetime.now(timezone.utc)}}
    )
    return {"status": "logged_out"}
