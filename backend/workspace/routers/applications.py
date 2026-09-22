from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect_database
from ..models import AccountApplication, ApplicationResponse
from ..security import password_hash, require_admin

router = APIRouter(tags=["account applications"])


@router.post("/account-applications", response_model=ApplicationResponse, status_code=201)
async def create_account_application(application: AccountApplication) -> dict[str, Any]:
    client, collection = connect_database()
    try:
        document = application.model_dump(exclude={"password"})
        document["password_hash"] = password_hash.hash(application.password)
        document.update(status="pending", submitted_at=datetime.now(timezone.utc))
        result = collection.insert_one(document)
        return {**document, "id": str(result.inserted_id)}
    finally:
        client.close()


@router.get("/account-applications", response_model=list[ApplicationResponse])
async def list_account_applications(_: dict[str, str] = Depends(require_admin)) -> list[dict[str, Any]]:
    client, collection = connect_database()
    try:
        documents = list(collection.find({"status": "pending"}).sort("submitted_at", -1))
        return [{**document, "id": str(document.pop("_id"))} for document in documents]
    finally:
        client.close()


@router.post("/account-applications/{application_id}/validate")
async def validate_account_application(application_id: str, _: dict[str, str] = Depends(require_admin)) -> dict[str, str]:
    client, collection = connect_database()
    try:
        try:
            object_id = ObjectId(application_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltigt ansöknings-ID") from error
        application = collection.find_one({"_id": object_id, "status": "pending"})
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        client["inventory-manager"]["Medlem"].insert_one({
            "name": application["name"], "email": application["email"],
            "password_hash": application["password_hash"], "role": "Medlem",
            "created_at": datetime.now(timezone.utc),
        })
        collection.update_one({"_id": object_id}, {"$set": {"status": "validated", "approved_role": "Medlem"}})
        return {"status": "validated", "role": "Medlem"}
    finally:
        client.close()


@router.post("/account-applications/{application_id}/reject")
async def reject_account_application(application_id: str, _: dict[str, str] = Depends(require_admin)) -> dict[str, str]:
    client, collection = connect_database()
    try:
        try:
            object_id = ObjectId(application_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltigt ansöknings-ID") from error
        result = collection.update_one({"_id": object_id, "status": "pending"}, {"$set": {"status": "rejected"}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Application not found")
        return {"status": "rejected"}
    finally:
        client.close()
