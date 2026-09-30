import os
import re
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..database import connect_database
from ..models import MaterialCreate
from ..security import require_admin, require_authenticated

router = APIRouter(tags=["materials"])


@router.get("/materials")
async def list_materials(_: dict[str, Any] = Depends(require_authenticated)) -> list[dict[str, Any]]:
    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        materials = database["material"].find().sort("name", 1)
        warehouse_names = {
            str(warehouse["_id"]): warehouse.get("name", "Okänt lager")
            for warehouse in database["warehouse"].find({}, {"name": 1})
        }
        return [
            {
                "id": str(material["_id"]),
                "sku": material.get("sku", ""),
                "name": material.get("name", ""),
                "category": material.get("category", "Förbrukning"),
                "quantity": material.get("quantity", 0),
                "minimum_stock": material.get("minimum_stock", 0),
                "status": material.get("status", "available"),
                "unit": material.get("unit", "st"),
                "location": material.get("location", "Okänd lagerplats"),
                "warehouse": warehouse_names.get(str(material.get("warehouse_id")), "Okänt lager"),
                "damaged_count": material.get("damaged_count", 0),
            }
            for material in materials
        ]
    finally:
        client.close()


@router.post("/materials", status_code=201)
async def create_material(
    material: MaterialCreate,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        warehouses = database["warehouse"]
        warehouse_name = material.warehouse.strip()
        warehouse = warehouses.find_one({
            "$or": [
                {"name": {"$regex": f"^{re.escape(warehouse_name)}$", "$options": "i"}},
                {"code": {"$regex": f"^{re.escape(warehouse_name)}$", "$options": "i"}},
            ]
        })
        if not warehouse:
            raise HTTPException(status_code=400, detail="Lager hittades inte. Kontrollera lagernamnet.")

        sku = material.sku.strip().upper()
        materials = database["material"]
        if materials.find_one({"sku": {"$regex": f"^{re.escape(sku)}$", "$options": "i"}}):
            raise HTTPException(status_code=409, detail="Artikelnumret används redan.")

        section = material.section.strip()
        quantity = material.quantity
        minimum_stock = 0
        record = {
            "sku": sku,
            "name": material.name.strip(),
            "category": material.category,
            "unit": material.unit.strip(),
            "quantity": quantity,
            "minimum_stock": minimum_stock,
            "damaged_count": material.damaged_count,
            "warehouse_id": warehouse["_id"],
            "section": section,
            "location": f"{warehouse.get('name', warehouse_name)} · {section}",
            "status": "low" if quantity <= minimum_stock else "available",
            "updated_at": datetime.now(timezone.utc),
        }
        result = materials.insert_one(record)
        try:
            database["audit_logs"].insert_one({
                "action": "material_created",
                "actor_id": actor.get("sub", ""),
                "actor_role": actor.get("role", "Admin"),
                "target_type": "material",
                "target_id": sku,
                "details": {
                    "name": record["name"],
                    "sku": sku,
                    "category": record["category"],
                    "quantity": quantity,
                    "unit": record["unit"],
                    "warehouse": warehouse.get("name", warehouse_name),
                    "location": record["location"],
                },
                "created_at": record["updated_at"],
            })
        except Exception:
            logging.exception("Could not record material creation activity")
        return {
            "id": str(result.inserted_id),
            "sku": sku,
            "name": record["name"],
            "category": record["category"],
            "quantity": quantity,
            "minimum_stock": minimum_stock,
            "status": record["status"],
            "unit": record["unit"],
            "location": record["location"],
            "damaged_count": record["damaged_count"],
        }
    finally:
        client.close()