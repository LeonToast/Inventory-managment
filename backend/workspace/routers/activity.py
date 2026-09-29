import logging
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pymongo.errors import PyMongoError

from ..database import activity_collection
from ..security import require_user
from ..timestamps import iso_utc

router = APIRouter(prefix="/activity", tags=["activity"])
logger = logging.getLogger(__name__)

LATEST = 5  # the feed keeps this many entries; the oldest is deleted when a new one is added

Kind = Literal["damage", "report", "material"]
TITLES: dict[str, str] = {
    "damage": "Skada rapporterad",
    "report": "Ny rapport publicerad",
    "material": "Nytt material skapat",
}


def record_activity(kind: Kind, description: str, actor: str) -> None:
    """Add one entry to the activity feed and drop whatever falls outside the latest LATEST.
    Called after the action itself has succeeded, so a failure here is logged instead of making
    the request fail."""
    try:
        collection = activity_collection()
        collection.insert_one(
            {
                "kind": kind,
                "title": TITLES[kind],
                "description": description,
                "created_by": actor,
                "created_at": datetime.now(timezone.utc),
            }
        )
        for stale in collection.find({}, {"_id": 1}).sort("_id", -1).skip(LATEST):
            collection.delete_one({"_id": stale["_id"]})
    except PyMongoError:
        logger.exception("Could not record %s activity", kind)


def activity_response(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "kind": document["kind"],
        "title": document["title"],
        "description": document["description"],
        "created_at": iso_utc(document["created_at"]),
    }


@router.get("")
def list_activity(_: dict[str, str] = Depends(require_user)) -> list[dict[str, Any]]:
    # An ObjectId starts with its creation time, so sorting on it (which is indexed) gives newest first.
    latest = activity_collection().find().sort("_id", -1).limit(LATEST)
    return [activity_response(item) for item in latest]
