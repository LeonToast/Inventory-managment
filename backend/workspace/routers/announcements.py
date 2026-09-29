from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..database import announcements_collection, parse_object_id
from ..security import require_admin, require_user
from ..timestamps import iso_utc
from .activity import record_activity

router = APIRouter(prefix="/announcements", tags=["announcements"])


class AnnouncementInput(BaseModel):
    # Anything else in the request, such as created_by, is ignored: the server sets it.
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=2000)
    category: Literal["Rapport", "Viktigt", "Driftinformation", "Status"]


def announcement_response(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document["title"],
        "text": document["text"],
        "category": document["category"],
        "created_at": iso_utc(document["created_at"]),
    }


@router.get("")
def list_announcements(_: dict[str, str] = Depends(require_user)) -> list[dict[str, Any]]:
    newest_first = announcements_collection().find().sort("created_at", -1)
    return [announcement_response(item) for item in newest_first]


@router.post("", status_code=201)
def create_announcement(
    announcement: AnnouncementInput, user: dict[str, str] = Depends(require_admin)
) -> dict[str, Any]:
    document = {
        **announcement.model_dump(),
        "created_by": user["sub"],
        "created_at": datetime.now(timezone.utc),
    }
    document["_id"] = announcements_collection().insert_one(document).inserted_id
    record_activity("report", announcement.title, user["sub"])
    return announcement_response(document)


@router.delete("/{announcement_id}", dependencies=[Depends(require_admin)])
def delete_announcement(announcement_id: str) -> dict[str, str]:
    result = announcements_collection().delete_one(
        {"_id": parse_object_id(announcement_id, "Ogiltigt meddelande-ID")}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meddelandet hittades inte")
    return {"status": "deleted"}
