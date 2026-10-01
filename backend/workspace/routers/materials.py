import os
import re
import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect_database
from ..models import MaterialCreate, MaterialFootprintUpdate, WarehouseCapacityUpdate
from ..security import require_admin, require_authenticated

router = APIRouter(tags=["materials"])


def warehouse_capacity(warehouse: dict[str, Any]) -> float | None:
    value = warehouse.get("capacity_m2")
    if value is None:
        value = warehouse.get("capacity")
    return float(value) if isinstance(value, (int, float)) else None


def measured_footprint(materials: list[dict[str, Any]]) -> tuple[float, int]:
    occupied_m2 = 0.0
    unmeasured_materials = 0
    for material in materials:
        length = material.get("footprint_length_cm")
        width = material.get("footprint_width_cm")
        if isinstance(length, (int, float)) and isinstance(width, (int, float)):
            occupied_m2 += length * width * max(int(material.get("quantity", 0)), 0) / 10_000
        else:
            unmeasured_materials += 1
    return occupied_m2, unmeasured_materials


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
                "footprint_length_cm": material.get("footprint_length_cm"),
                "footprint_width_cm": material.get("footprint_width_cm"),
            }
            for material in materials
        ]
    finally:
        client.close()


@router.get("/warehouse-capacity")
async def list_warehouse_capacity(_: dict[str, Any] = Depends(require_authenticated)) -> list[dict[str, Any]]:
    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        materials_by_warehouse: dict[str, list[dict[str, Any]]] = {}
        for material in database["material"].find(
            {},
            {"warehouse_id": 1, "quantity": 1, "footprint_length_cm": 1, "footprint_width_cm": 1},
        ):
            warehouse_id = str(material.get("warehouse_id", ""))
            materials_by_warehouse.setdefault(warehouse_id, []).append(material)

        result = []
        for warehouse in database["warehouse"].find().sort("name", 1):
            warehouse_materials = materials_by_warehouse.get(str(warehouse["_id"]), [])
            occupied_m2, unmeasured_materials = measured_footprint(warehouse_materials)
            capacity_m2 = warehouse_capacity(warehouse)
            utilization_percent = round(occupied_m2 / capacity_m2 * 100, 2) if capacity_m2 else None
            result.append({
                "id": str(warehouse["_id"]),
                "name": warehouse.get("name", "Okänt lager"),
                "capacity_m2": capacity_m2,
                "occupied_m2": round(occupied_m2, 2),
                "unmeasured_materials": unmeasured_materials,
                "utilization_percent": utilization_percent,
                "remaining_percent": (
                    max(0, round(100 - utilization_percent, 2))
                    if utilization_percent is not None and unmeasured_materials == 0
                    else None
                ),
            })
        return result
    finally:
        client.close()


@router.patch("/materials/{material_id}/footprint")
async def update_material_footprint(
    material_id: str,
    footprint: MaterialFootprintUpdate,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, float | str]:
    try:
        object_id = ObjectId(material_id)
    except Exception as error:
        raise HTTPException(status_code=400, detail="Ogiltigt material-ID.") from error

    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        materials = database["material"]
        material = materials.find_one({"_id": object_id})
        if not material:
            raise HTTPException(status_code=404, detail="Materialet hittades inte.")
        warehouse = database["warehouse"].find_one({"_id": material.get("warehouse_id")})
        if warehouse:
            stored_materials = list(materials.find({"warehouse_id": material["warehouse_id"]}))
            current, unmeasured = measured_footprint(stored_materials)
            old_area = 0.0
            had_footprint = isinstance(material.get("footprint_length_cm"), (int, float)) and isinstance(material.get("footprint_width_cm"), (int, float))
            if had_footprint:
                old_area = material["footprint_length_cm"] * material["footprint_width_cm"] * max(int(material.get("quantity", 0)), 0) / 10_000
            proposed = current - old_area + footprint.footprint_length_cm * footprint.footprint_width_cm * max(int(material.get("quantity", 0)), 0) / 10_000
            if not had_footprint:
                unmeasured -= 1
            capacity = warehouse_capacity(warehouse)
            if unmeasured == 0 and capacity is not None and proposed > capacity:
                raise HTTPException(status_code=409, detail=f"Måtten skulle överskrida lagrets kapacitet på {capacity:g} m².")
        result = materials.update_one(
            {"_id": object_id},
            {"$set": {
                "footprint_length_cm": footprint.footprint_length_cm,
                "footprint_width_cm": footprint.footprint_width_cm,
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Materialet hittades inte.")
        try:
            database["audit_logs"].insert_one({
                "action": "material_footprint_updated",
                "actor_id": actor.get("sub", ""),
                "actor_role": actor.get("role", "Admin"),
                "target_type": "material",
                "target_id": material_id,
                "details": {
                    "footprint_length_cm": footprint.footprint_length_cm,
                    "footprint_width_cm": footprint.footprint_width_cm,
                },
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            logging.exception("Could not record material footprint update")
        return {
            "id": material_id,
            "footprint_length_cm": footprint.footprint_length_cm,
            "footprint_width_cm": footprint.footprint_width_cm,
        }
    finally:
        client.close()


@router.patch("/warehouse-capacity/{warehouse_id}")
async def update_warehouse_capacity(
    warehouse_id: str,
    update: WarehouseCapacityUpdate,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, float | str]:
    try:
        object_id = ObjectId(warehouse_id)
    except Exception as error:
        raise HTTPException(status_code=400, detail="Ogiltigt lager-ID.") from error

    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        warehouse = database["warehouse"].find_one({"_id": object_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Lagret hittades inte.")
        stored_materials = list(database["material"].find({"warehouse_id": object_id}))
        occupied_m2, _ = measured_footprint(stored_materials)
        if update.capacity_m2 < occupied_m2:
            raise HTTPException(status_code=409, detail=f"Kapaciteten kan inte vara mindre än den uppmätta golvytan på {occupied_m2:.2f} m².")
        result = database["warehouse"].update_one(
            {"_id": object_id},
            {"$set": {"capacity_m2": update.capacity_m2, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Lagret hittades inte.")
        try:
            database["audit_logs"].insert_one({
                "action": "warehouse_capacity_updated",
                "actor_id": actor.get("sub", ""),
                "actor_role": actor.get("role", "Admin"),
                "target_type": "warehouse",
                "target_id": warehouse_id,
                "details": {"capacity_m2": update.capacity_m2},
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            logging.exception("Could not record warehouse capacity update")
        warehouse = database["warehouse"].find_one({"_id": object_id}, {"name": 1})
        return {"id": warehouse_id, "name": warehouse.get("name", "Okänt lager"), "capacity_m2": update.capacity_m2}
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

        capacity = warehouse_capacity(warehouse)
        if capacity is not None:
            current_materials = list(materials.find({"warehouse_id": warehouse["_id"]}))
            occupied_m2, _ = measured_footprint(current_materials)
            added_area = material.footprint_length_cm * material.footprint_width_cm * material.quantity / 10_000
            if occupied_m2 + added_area > capacity:
                raise HTTPException(status_code=409, detail=f"Materialet skulle överskrida lagrets kapacitet på {capacity:g} m².")

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
            "footprint_length_cm": material.footprint_length_cm,
            "footprint_width_cm": material.footprint_width_cm,
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
            "footprint_length_cm": record["footprint_length_cm"],
            "footprint_width_cm": record["footprint_width_cm"],
        }
    finally:
        client.close()