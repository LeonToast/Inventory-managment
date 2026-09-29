from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..database import members_collection, parse_object_id
from ..models import RoleUpdate
from ..security import require_admin
from ..timestamps import as_utc, iso_utc

router = APIRouter(prefix="/members", tags=["members"])

INVALID_ID = "Ogiltigt medlems-ID"
# The browser sends a heartbeat every 60 seconds; allow for a missed one before showing offline.
ONLINE_WINDOW = timedelta(seconds=150)


def is_online(member: dict[str, Any], now: datetime) -> bool:
    """Online = logged in (no logout since the last login) and seen within the heartbeat window."""
    login = as_utc(member.get("last_login_at"))
    logout = as_utc(member.get("last_logout_at"))
    seen = as_utc(member.get("last_seen_at"))
    if not login or not seen:
        return False
    if logout and logout >= login:
        return False
    return now - seen <= ONLINE_WINDOW


@router.get("")
def list_members() -> list[dict[str, Any]]:
    fields = {
        "name": 1,
        "email": 1,
        "role": 1,
        "last_login_at": 1,
        "last_logout_at": 1,
        "last_seen_at": 1,
    }
    members = members_collection().find({}, fields).sort("created_at", -1)
    now = datetime.now(timezone.utc)
    return [
        {
            "id": str(member["_id"]),
            "name": member.get("name", ""),
            "email": member.get("email", ""),
            "role": member.get("role", "Medlem"),
            "last_login_at": iso_utc(member.get("last_login_at")),
            "last_logout_at": iso_utc(member.get("last_logout_at")),
            "online": is_online(member, now),
        }
        for member in members
    ]


@router.delete("/{member_id}", dependencies=[Depends(require_admin)])
def delete_member(member_id: str) -> dict[str, str]:
    result = members_collection().delete_one({"_id": parse_object_id(member_id, INVALID_ID)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Medlem hittades inte")
    return {"status": "deleted"}


@router.patch("/{member_id}/role", dependencies=[Depends(require_admin)])
def update_member_role(member_id: str, update: RoleUpdate) -> dict[str, str]:
    result = members_collection().update_one(
        {"_id": parse_object_id(member_id, INVALID_ID)}, {"$set": {"role": update.role}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Medlem hittades inte")
    return {"status": "updated", "role": update.role}
