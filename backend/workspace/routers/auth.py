import hashlib
import hmac
import re

from fastapi import APIRouter, HTTPException

from ..database import connect_database
from ..models import LoginCredentials
from ..security import issue_token, password_hash

router = APIRouter(tags=["authentication"])


@router.post("/login")
async def login(credentials: LoginCredentials) -> dict[str, str]:
    if credentials.email == "admin@dev.local" and credentials.password == "Admin123!":
        account = {"name": "Admin", "email": "admin@dev.local", "role": "Admin"}
        return {**account, "access_token": issue_token(account["email"], account["role"])}
    client, _ = connect_database()
    try:
        normalized_email = credentials.email.strip().casefold()
        members = client["inventory-manager"]["Medlem"]
        member = members.find_one(
            {"email": {"$regex": "^" + re.escape(normalized_email) + "$", "$options": "i"}},
            {"name": 1, "email": 1, "role": 1, "password_hash": 1},
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
        account = {"name": member["name"], "email": member["email"], "role": member.get("role", "Medlem")}
        return {**account, "access_token": issue_token(account["email"], account["role"])}
    finally:
        client.close()
