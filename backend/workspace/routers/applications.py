from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from ..database import applications_collection, members_collection, parse_object_id
from ..models import AccountApplication, ApplicationResponse
from ..security import password_hash, require_admin

router = APIRouter(prefix="/account-applications", tags=["account applications"])

INVALID_ID = "Ogiltigt ansöknings-ID"


@router.post("", response_model=ApplicationResponse, status_code=201)
def create_account_application(application: AccountApplication) -> dict[str, Any]:
    document = application.model_dump(exclude={"password"})
    document.update(
        password_hash=password_hash.hash(application.password),
        status="pending",
        submitted_at=datetime.now(timezone.utc),
    )
    result = applications_collection().insert_one(document)
    return {**document, "id": str(result.inserted_id)}


@router.get("", response_model=list[ApplicationResponse], dependencies=[Depends(require_admin)])
def list_account_applications() -> list[dict[str, Any]]:
    documents = (
        applications_collection()
        .find({"status": "pending"}, {"name": 1, "email": 1, "status": 1, "submitted_at": 1})
        .sort("submitted_at", -1)
    )
    return [{**document, "id": str(document.pop("_id"))} for document in documents]


@router.post("/{application_id}/validate", dependencies=[Depends(require_admin)])
def validate_account_application(application_id: str) -> dict[str, str]:
    # Claim the application atomically so concurrent validations cannot create duplicate members.
    application = applications_collection().find_one_and_update(
        {"_id": parse_object_id(application_id, INVALID_ID), "status": "pending"},
        {"$set": {"status": "validated", "approved_role": "Medlem"}},
        projection={"name": 1, "email": 1, "password_hash": 1},
        return_document=ReturnDocument.BEFORE,
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    try:
        members_collection().insert_one(
            {
                "name": application["name"],
                "email": application["email"],
                "password_hash": application["password_hash"],
                "role": "Medlem",
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception:
        applications_collection().update_one(
            {"_id": application["_id"]},
            {"$set": {"status": "pending"}, "$unset": {"approved_role": ""}},
        )
        raise
    return {"status": "validated", "role": "Medlem"}


@router.delete("/{application_id}", dependencies=[Depends(require_admin)])
def reject_account_application(application_id: str) -> dict[str, str]:
    result = applications_collection().delete_one(
        {"_id": parse_object_id(application_id, INVALID_ID), "status": "pending"}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"status": "deleted"}
