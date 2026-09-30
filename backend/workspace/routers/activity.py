import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from ..database import connect_database
from ..security import require_authenticated

router = APIRouter(tags=["activity"])

VISIBLE_ACTIVITY_ACTIONS = [
    "material_created",
    "shipment_created",
    "shipment_delivered",
    "shipment_cancelled",
]


def format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value or "")


@router.get("/activity-history")
async def list_activity(actor: dict[str, Any] = Depends(require_authenticated)) -> list[dict[str, Any]]:
    client, _ = connect_database()
    try:
        logs = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]["audit_logs"]
        if actor.get("role") == "Admin":
            query: dict[str, Any] = {"action": {"$in": ["login", *VISIBLE_ACTIVITY_ACTIONS]}}
        else:
            query = {
                "$or": [
                    {"action": {"$in": VISIBLE_ACTIVITY_ACTIONS}},
                    {"action": "login", "actor_id": actor.get("sub", "")},
                ]
            }
        entries = logs.find(query).sort("created_at", -1).limit(50)
        return [
            {
                "id": str(entry["_id"]),
                "action": entry.get("action", ""),
                "actor_id": entry.get("actor_id", ""),
                "actor_name": entry.get("actor_name", entry.get("actor_id", "Okänd användare")),
                "actor_role": entry.get("actor_role", ""),
                "details": entry.get("details", {}),
                "created_at": format_timestamp(entry.get("created_at")),
            }
            for entry in entries
        ]
    finally:
        client.close()