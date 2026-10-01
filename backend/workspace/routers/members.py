import os
from typing import Any, cast

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect_database
from ..models import RoleUpdate
from ..security import require_admin

router = APIRouter(tags=["members"])


def member_collection(client: Any) -> Any:
    return client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]["Medlem"]


@router.get("/members")
async def list_members() -> list[dict[str, str]]:
    client, _ = connect_database()
    try:
        members = member_collection(client).find({}, {"name": 1, "email": 1, "role": 1}).sort("created_at", -1)
        return [
            {"id": str(member["_id"]), "name": member.get("name", ""),
             "email": member.get("email", ""), "role": "Worker" if member.get("role") in {"Medlem", "Worker"} else member.get("role", "Worker")}
            for member in members
        ]
    finally:
        client.close()


@router.delete("/members/{member_id}")
async def delete_member(member_id: str, _: dict[str, Any] = Depends(require_admin)) -> dict[str, str]:
    client, _ = connect_database()
    try:
        try:
            object_id = ObjectId(member_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltigt medlems-ID") from error
        result = cast(Any, member_collection(client)).delete_one({"_id": object_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Medlem hittades inte")
        return {"status": "deleted"}
    finally:
        client.close()


@router.patch("/members/{member_id}/role")
async def update_member_role(member_id: str, update: RoleUpdate, _: dict[str, Any] = Depends(require_admin)) -> dict[str, str]:
    client, _ = connect_database()
    try:
        try:
            object_id = ObjectId(member_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltigt medlems-ID") from error
        result = cast(Any, member_collection(client)).update_one(
            {"_id": object_id}, {"$set": {"role": update.role}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Medlem hittades inte")
        return {"status": "updated", "role": update.role}
    finally:
        client.close()
