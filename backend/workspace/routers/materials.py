from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument

from ..database import materials_collection, parse_object_id, reports_collection
from ..security import require_admin, require_user
from .activity import record_activity

router = APIRouter(prefix="/materials", tags=["materials"])

INVALID_ID = "Ogiltigt material-ID"
NOT_FOUND = "Materialet hittades inte"


class MaterialInput(BaseModel):
    # Anything else in the request is ignored: a material is stored as exactly these five fields.
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    name: str = Field(min_length=1, max_length=100)
    category: Literal["Förbrukning", "Elektronik", "Utrustning"]
    warehouse: str = Field(default="", max_length=50)
    quantity: int = Field(ge=0, le=1_000_000_000)
    unit: str = Field(min_length=1, max_length=20)


def material_response(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "category": document["category"],
        "warehouse": document.get("warehouse", ""),
        "quantity": document["quantity"],
        "unit": document["unit"],
    }


@router.get("")
def list_materials(_: dict[str, str] = Depends(require_user)) -> list[dict[str, Any]]:
    # An ObjectId starts with its creation time, so sorting on it lists the oldest first.
    return [material_response(item) for item in materials_collection().find().sort("_id", 1)]


@router.post("", status_code=201)
def create_material(
    material: MaterialInput, user: dict[str, str] = Depends(require_admin)
) -> dict[str, Any]:
    document = material.model_dump()
    result = materials_collection().insert_one(document)
    document["_id"] = result.inserted_id
    details = [material.name, f"{material.quantity} {material.unit}", material.warehouse]
    record_activity("material", " · ".join(part for part in details if part), user["sub"])
    return material_response(document)


@router.patch("/{material_id}", dependencies=[Depends(require_admin)])
def update_material(material_id: str, material: MaterialInput) -> dict[str, Any]:
    updated = materials_collection().find_one_and_update(
        {"_id": parse_object_id(material_id, INVALID_ID)},
        {"$set": material.model_dump()},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return material_response(updated)


@router.delete("/{material_id}", dependencies=[Depends(require_admin)])
def delete_material(material_id: str) -> dict[str, str]:
    object_id = parse_object_id(material_id, INVALID_ID)
    if not materials_collection().find_one({"_id": object_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    # Damage reports refer to a material by its id.
    has_damage_reports = reports_collection().find_one(
        {"kind": "damage", "material_id": str(object_id)}, {"_id": 1}
    )
    if has_damage_reports:
        raise HTTPException(
            status_code=409, detail="Materialet har rapporterade skador och kan inte tas bort."
        )
    materials_collection().delete_one({"_id": object_id})
    return {"status": "deleted"}
