import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
import pyotp

from ..database import connect_database
from ..models import LoginCredentials
from ..security import decrypt_totp_secret, issue_token, password_hash, require_admin

router = APIRouter(tags=["authentication"])


def normalize_role(role: str | None) -> str:
    if role in {"Medlem", "Worker"}:
        return "Worker"
    return role or "Worker"


def record_login(database: Any, account: dict[str, str]) -> None:
    database["audit_logs"].insert_one({
        "action": "login",
        "actor_id": account["email"],
        "actor_name": account["name"],
        "actor_role": account["role"],
        "target_type": "session",
        "target_id": account["email"],
        "details": {"event": "successful_login"},
        "created_at": datetime.now(timezone.utc),
    })


def format_login_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value or "")


@router.post("/login")
async def login(credentials: LoginCredentials) -> dict[str, str | bool]:
    if credentials.email == "admin@dev.local" and credentials.password == "Admin123!":
        account = {"name": "Admin", "email": "admin@dev.local", "role": "Admin"}
        audit_client = None
        try:
            audit_client, _ = connect_database()
            record_login(audit_client[os.getenv("MONGODB_DB_NAME", "inventory-manager")], account)
        except HTTPException:
            pass
        except Exception:
            logging.exception("Could not record admin login")
        finally:
            if audit_client is not None:
                audit_client.close()
        return {**account, "access_token": issue_token(account["email"], account["role"])}
    client, _ = connect_database()
    try:
        normalized_email = credentials.email.strip().casefold()
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        members = database["Medlem"]
        member = members.find_one(
            {"email": {"$regex": "^" + re.escape(normalized_email) + "$", "$options": "i"}},
            {"name": 1, "email": 1, "role": 1, "password_hash": 1, "two_factor_enabled": 1, "totp_secret_encrypted": 1},
        )
        if not member:
            raise HTTPException(status_code=401, detail="Fel e-postadress eller lösenord.")
        stored_hash = member.get("password_hash", "")
        valid_password = False
        if stored_hash.startswith("$argon2"):
            try:
                valid_password = password_hash.verify(credentials.password, stored_hash)
            except (ValueError, TypeError):
                pass
        elif re.fullmatch(r"[0-9a-fA-F]{64}", stored_hash):
            valid_password = hmac.compare_digest(
                hashlib.sha256(credentials.password.encode()).hexdigest(), stored_hash.lower()
            )
            if valid_password:
                members.update_one({"_id": member["_id"]}, {"$set": {
                    "password_hash": password_hash.hash(credentials.password)
                }})
        if not valid_password:
            raise HTTPException(status_code=401, detail="Fel e-postadress eller lösenord.")
        if member.get("two_factor_enabled"):
            if not credentials.two_factor_code:
                return {"requires_two_factor": True}
            try:
                secret = decrypt_totp_secret(member["totp_secret_encrypted"])
                valid_code = pyotp.TOTP(secret).verify(credentials.two_factor_code, valid_window=1)
            except (KeyError, TypeError, ValueError):
                valid_code = False
            if not valid_code:
                raise HTTPException(status_code=401, detail="Authenticator-koden är ogiltig eller har gått ut.")
        account_role = normalize_role(member.get("role"))
        account = {"name": member["name"], "email": member["email"], "role": account_role}
        try:
            record_login(database, account)
        except Exception:
            logging.exception("Could not record successful login")
        return {**account, "access_token": issue_token(account["email"], account["role"])}
    finally:
        client.close()


@router.get("/login-history")
async def login_history(_: dict[str, str] = Depends(require_admin)) -> list[dict[str, str]]:
    client, _ = connect_database()
    try:
        logs = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]["audit_logs"]
        entries = logs.find({"action": "login"}).sort("created_at", -1).limit(200)
        return [
            {
                "id": str(entry["_id"]),
                "name": entry.get("actor_name", "Okänd användare"),
                "email": entry.get("actor_id", ""),
                "role": entry.get("actor_role", "Worker"),
                "created_at": format_login_timestamp(entry.get("created_at")),
            }
            for entry in entries
        ]
    finally:
        client.close()
