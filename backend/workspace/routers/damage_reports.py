from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from ..database import reports_collection
from ..security import require_user

router = APIRouter(prefix="/damage-reports", tags=["damage reports"])

MaterialId = Literal["MAT-1024", "MAT-1180", "MAT-2042", "MAT-2371"]


class DamageReportInput(BaseModel):
    material_id: MaterialId
    serial_number: str = Field(min_length=1, max_length=100)


def report_response(document: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(document["_id"]),
        "material_id": document["material_id"],
        "serial_number": document["serial_number"],
        "reported_at": document["reported_at"].isoformat(),
    }


@router.get("")
def list_damage_reports(_: dict[str, str] = Depends(require_user)) -> list[dict[str, str]]:
    reports = reports_collection().find(
        {"kind": "damage"}, {"material_id": 1, "serial_number": 1, "reported_at": 1}
    ).sort("reported_at", -1)
    return [report_response(item) for item in reports]


@router.post("", status_code=201)
def create_damage_report(
    report: DamageReportInput,
    user: dict[str, str] = Depends(require_user),
) -> dict[str, str]:
    serial_number = report.serial_number.strip().upper()
    if not serial_number:
        raise HTTPException(status_code=422, detail="Ange ett serienummer")

    document = {
        "kind": "damage",
        "material_id": report.material_id,
        "serial_number": serial_number,
        "reported_by": user["sub"],
        "reported_at": datetime.now(timezone.utc),
    }
    try:
        result = reports_collection().insert_one(document)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail="Serienumret är redan rapporterat som skadat") from error
    document["_id"] = result.inserted_id
    return report_response(document)
