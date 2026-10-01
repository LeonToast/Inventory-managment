import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
import pyotp

from ..database import connect_database
from ..models import AccountApplication, ApplicationResponse, TwoFactorSetupRequest
from ..security import encrypt_totp_secret, password_hash, require_admin

router = APIRouter(tags=["account applications"])


@router.post("/account-applications/two-factor/setup")
async def setup_application_two_factor(request: TwoFactorSetupRequest) -> dict[str, str]:
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    return {
        "secret": secret,
        "otpauth_uri": totp.provisioning_uri(name=str(request.email), issuer_name="Smart Lagring"),
    }


@router.post("/account-applications", response_model=ApplicationResponse, status_code=201)
async def create_account_application(application: AccountApplication) -> dict[str, Any]:
    client, collection = connect_database()
    try:
        if application.two_factor_secret and application.two_factor_code:
            if not pyotp.TOTP(application.two_factor_secret).verify(application.two_factor_code, valid_window=1):
                raise HTTPException(status_code=400, detail="Authenticator-koden stämmer inte.")
        document = application.model_dump(exclude={"password", "two_factor_code"}, exclude_none=True)
        if application.two_factor_secret:
            document["totp_secret_encrypted"] = encrypt_totp_secret(application.two_factor_secret)
            document["two_factor_enabled"] = True
        else:
            document["two_factor_enabled"] = False
        document.pop("two_factor_secret", None)
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
        member = {
            "name": application["name"], "email": application["email"],
            "password_hash": application["password_hash"], "role": "Worker",
            "created_at": datetime.now(timezone.utc),
            "two_factor_enabled": application.get("two_factor_enabled", False),
        }
        if application.get("two_factor_enabled"):
            member["totp_secret_encrypted"] = application["totp_secret_encrypted"]
        client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]["Medlem"].insert_one(member)
        collection.update_one({"_id": object_id}, {"$set": {"status": "validated", "approved_role": "Worker"}})
        return {"status": "validated", "role": "Worker"}
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
