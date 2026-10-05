import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect_database
from ..models import ReportCreate
from ..security import require_admin, require_authenticated

router = APIRouter(tags=["reports"])

REPORT_TITLES = {
    "inventory": "Lageröversikt",
    "deliveries": "Leveransrapport",
    "low_stock": "Rapport om lågt lagersaldo",
    "damaged": "Skaderapport",
    "capacity": "Lagerutrymmesrapport",
    "activity": "Aktivitetsrapport",
}


def serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    return value


def serialize_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(report["_id"]),
        "title": report.get("title", "Rapport"),
        "report_type": report.get("report_type", ""),
        "period": report.get("period", {}),
        "warehouse": report.get("warehouse", "Alla lager"),
        "description": report.get("description", ""),
        "summary": report.get("summary", {}),
        "rows": serialize_value(report.get("rows", [])),
        "generated_at": serialize_value(report.get("generated_at")),
    }


def date_filter(start_date: date, end_date: date) -> dict[str, datetime]:
    return {
        "$gte": datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        "$lt": datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
    }


@router.get("/reports")
async def list_reports(_: dict[str, Any] = Depends(require_authenticated)) -> list[dict[str, Any]]:
    client, _ = connect_database()
    try:
        reports = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]["generated_reports"]
        return [serialize_report(report) for report in reports.find().sort("generated_at", -1).limit(50)]
    finally:
        client.close()


@router.post("/reports", status_code=201)
async def create_report(
    request: ReportCreate,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    warehouse_id: ObjectId | None = None
    if request.warehouse_id:
        try:
            warehouse_id = ObjectId(request.warehouse_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltigt lager-ID.") from error

    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        warehouses = database["warehouse"]
        warehouse_filter: dict[str, Any] = {"_id": warehouse_id} if warehouse_id else {}
        warehouse_docs = list(warehouses.find(warehouse_filter).sort("name", 1))
        if warehouse_id and not warehouse_docs:
            raise HTTPException(status_code=404, detail="Lagret hittades inte.")

        warehouse_names = {str(warehouse["_id"]): warehouse.get("name", "Okänt lager") for warehouse in warehouse_docs}
        warehouse_name = warehouse_names.get(str(warehouse_id), "Alla lager") if warehouse_id else "Alla lager"
        rows: list[dict[str, Any]] = []
        summary: dict[str, Any]

        if request.report_type in {"inventory", "low_stock", "damaged"}:
            query: dict[str, Any] = {}
            if warehouse_id:
                query["warehouse_id"] = warehouse_id
            if request.report_type == "low_stock":
                query["$expr"] = {"$lte": ["$quantity", "$minimum_stock"]}
            elif request.report_type == "damaged":
                query["damaged_count"] = {"$gt": 0}

            materials = list(database["material"].find(query).sort("name", 1))
            rows = [
                {
                    "name": material.get("name", "Okänt material"),
                    "sku": material.get("sku", ""),
                    "warehouse": warehouse_names.get(str(material.get("warehouse_id")), "Okänt lager"),
                    "quantity": int(material.get("quantity", 0)),
                    "minimum_stock": int(material.get("minimum_stock", 0)),
                    "damaged_count": int(material.get("damaged_count", 0)),
                    "unit": material.get("unit", "st"),
                    "location": material.get("location", "Okänd lagerplats"),
                }
                for material in materials
            ]
            summary = {
                "items": len(rows),
                "quantity": sum(row["quantity"] for row in rows),
                "damaged_count": sum(row["damaged_count"] for row in rows),
            }
        elif request.report_type == "deliveries":
            query = {
                "direction": "outgoing",
                "created_at": date_filter(request.start_date, request.end_date),
            }
            if warehouse_id:
                query["warehouse_id"] = warehouse_id
            deliveries = list(database["deliveries"].find(query).sort("created_at", -1))
            rows = [
                {
                    "shipment_id": item.get("shipment_id", ""),
                    "customer_name": item.get("customer_name", ""),
                    "material_name": item.get("material_name", ""),
                    "sku": item.get("sku", ""),
                    "warehouse": item.get("warehouse", "Okänt lager"),
                    "quantity": int(item.get("quantity", 0)),
                    "unit": item.get("unit", "st"),
                    "status": item.get("status", "shipped"),
                    "created_at": serialize_value(item.get("created_at")),
                }
                for item in deliveries
            ]
            summary = {"deliveries": len(rows), "quantity": sum(row["quantity"] for row in rows)}
        elif request.report_type == "capacity":
            materials_by_warehouse: dict[str, list[dict[str, Any]]] = {}
            for material in database["material"].find(
                {"warehouse_id": {"$in": [item["_id"] for item in warehouse_docs]}}
                if warehouse_id
                else {}
            ):
                materials_by_warehouse.setdefault(str(material.get("warehouse_id")), []).append(material)

            for warehouse in warehouse_docs:
                items = materials_by_warehouse.get(str(warehouse["_id"]), [])
                occupied_m2 = 0.0
                unmeasured_materials = 0
                for material in items:
                    length = material.get("footprint_length_cm")
                    width = material.get("footprint_width_cm")
                    if isinstance(length, (int, float)) and isinstance(width, (int, float)):
                        occupied_m2 += length * width * max(int(material.get("quantity", 0)), 0) / 10_000
                    else:
                        unmeasured_materials += 1
                capacity = warehouse.get("capacity_m2", warehouse.get("capacity"))
                rows.append({
                    "warehouse": warehouse.get("name", "Okänt lager"),
                    "capacity_m2": capacity,
                    "occupied_m2": round(occupied_m2, 2),
                    "unmeasured_materials": unmeasured_materials,
                    "utilization_percent": round(occupied_m2 / capacity * 100, 2) if capacity else None,
                })
            summary = {"warehouses": len(rows), "unmeasured_materials": sum(row["unmeasured_materials"] for row in rows)}
        else:
            query = {"created_at": date_filter(request.start_date, request.end_date)}
            if warehouse_id:
                query["details.warehouse"] = warehouse_name
            entries = list(database["audit_logs"].find(query).sort("created_at", -1).limit(1000))
            rows = [
                {
                    "action": entry.get("action", ""),
                    "actor": entry.get("actor_name", entry.get("actor_id", "")),
                    "details": entry.get("details", {}),
                    "created_at": serialize_value(entry.get("created_at")),
                }
                for entry in entries
            ]
            summary = {"activities": len(rows)}

        now = datetime.now(timezone.utc)
        report = {
            "title": REPORT_TITLES[request.report_type],
            "report_type": request.report_type,
            "period": {"start": request.start_date.isoformat(), "end": request.end_date.isoformat()},
            "warehouse": warehouse_name,
            "warehouse_id": warehouse_id,
            "description": request.description.strip(),
            "summary": summary,
            "rows": rows,
            "created_by": actor.get("sub", ""),
            "generated_at": now,
        }
        result = database["generated_reports"].insert_one(report)
        report["_id"] = result.inserted_id
        return serialize_report(report)
    finally:
        client.close()
