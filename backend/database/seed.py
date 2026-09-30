from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.database.init_db import initialize_database
from backend.workspace.security import password_hash


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def seed_database() -> dict[str, int]:
    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "inventory-manager")
    if not mongo_uri:
        raise RuntimeError("MONGODB_URI is not configured")

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    initialize_database(db)

    now = datetime.now(timezone.utc)

    admin_email = "admin@dev.local"
    admin_member = db["Medlem"].find_one({"email": {"$regex": f"^{admin_email}$", "$options": "i"}})
    if not admin_member:
        db["Medlem"].insert_one({
            "name": "Admin",
            "email": admin_email,
            "password_hash": password_hash.hash("Admin123!"),
            "role": "Admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

    worker_email = "worker@dev.local"
    worker_member = db["Medlem"].find_one({"email": {"$regex": f"^{worker_email}$", "$options": "i"}})
    if not worker_member:
        db["Medlem"].insert_one({
            "name": "Worker",
            "email": worker_email,
            "password_hash": password_hash.hash("Worker123!"),
            "role": "Worker",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

    warehouse_docs = [
        {"name": "Lager A", "code": "WH-A", "location": "Stockholm", "capacity": 1200, "manager_id": None, "created_at": now},
        {"name": "Lager B", "code": "WH-B", "location": "Gothenburg", "capacity": 900, "manager_id": None, "created_at": now},
        {"name": "Lager C", "code": "WH-C", "location": "Malmö", "capacity": 700, "manager_id": None, "created_at": now},
    ]
    warehouse_ids: dict[str, object] = {}
    for warehouse in warehouse_docs:
        existing = db["warehouse"].find_one({"code": warehouse["code"]})
        if existing:
            warehouse_ids[warehouse["code"]] = existing["_id"]
        else:
            result = db["warehouse"].insert_one(warehouse)
            warehouse_ids[warehouse["code"]] = result.inserted_id

    materials = [
        {
            "sku": "MAT-1024",
            "name": "Kabeltrumma 25m",
            "category": "Elektronik",
            "unit": "st",
            "quantity": 12,
            "minimum_stock": 6,
            "damaged_count": 1,
            "warehouse_id": warehouse_ids["WH-A"],
            "section": "Sektion 3",
            "location": "Lager A · Sektion 3",
            "status": "available",
            "updated_at": now,
        },
        {
            "sku": "MAT-1180",
            "name": "Skyddshandskar",
            "category": "Förbrukning",
            "unit": "par",
            "quantity": 248,
            "minimum_stock": 50,
            "damaged_count": 2,
            "warehouse_id": warehouse_ids["WH-B"],
            "section": "Sektion 1",
            "location": "Lager B · Sektion 1",
            "status": "available",
            "updated_at": now,
        },
        {
            "sku": "MAT-2042",
            "name": "Pallställ 1200 kg",
            "category": "Utrustning",
            "unit": "st",
            "quantity": 6,
            "minimum_stock": 3,
            "damaged_count": 1,
            "warehouse_id": warehouse_ids["WH-A"],
            "section": "Sektion 5",
            "location": "Lager A · Sektion 5",
            "status": "low",
            "updated_at": now,
        },
        {
            "sku": "MAT-2371",
            "name": "Fraktsedlar",
            "category": "Förbrukning",
            "unit": "st",
            "quantity": 820,
            "minimum_stock": 200,
            "damaged_count": 2,
            "warehouse_id": warehouse_ids["WH-C"],
            "section": "Sektion 2",
            "location": "Lager C · Sektion 2",
            "status": "available",
            "updated_at": now,
        },
    ]
    for material in materials:
        db["material"].update_one(
            {"sku": material["sku"]},
            {"$set": material},
            upsert=True,
        )

    delivery_docs = [
        {
            "delivery_id": "LEV-24018",
            "supplier": "Nordic Supply AB",
            "warehouse_id": warehouse_ids["WH-A"],
            "scheduled_at": now,
            "received_at": None,
            "status": "in_transit",
            "items": [{"sku": "MAT-1024", "name": "Kabeltrumma 25m", "quantity": 24, "received_quantity": 0, "unit": "st"}],
            "notes": "Leverans på väg från huvudlager",
            "created_by": admin_email,
            "created_at": now,
        },
        {
            "delivery_id": "LEV-24017",
            "supplier": "Pack & Frakt Sverige",
            "warehouse_id": warehouse_ids["WH-C"],
            "scheduled_at": now,
            "received_at": now,
            "status": "received",
            "items": [{"sku": "MAT-2371", "name": "Fraktsedlar", "quantity": 820, "received_quantity": 820, "unit": "st"}],
            "notes": "Leverans mottagen och registrerad",
            "created_by": admin_email,
            "created_at": now,
        },
        {
            "delivery_id": "LEV-24016",
            "supplier": "ScanTech Nordic",
            "warehouse_id": warehouse_ids["WH-B"],
            "scheduled_at": now,
            "received_at": None,
            "status": "issue",
            "items": [{"sku": "MAT-1180", "name": "Streckkodsläsare", "quantity": 18, "received_quantity": 0, "unit": "st"}],
            "notes": "Avvikelse: paketet saknar delar",
            "created_by": admin_email,
            "created_at": now,
        },
    ]
    for delivery in delivery_docs:
        db["deliveries"].update_one(
            {"delivery_id": delivery["delivery_id"]},
            {"$set": delivery},
            upsert=True,
        )

    report_docs = [
        {
            "title": "Månadsrapport · Oktober",
            "type": "report",
            "content": "Sammanfattning av lagerstatus, leveranser och avvikelser för oktober.",
            "created_by": admin_email,
            "created_at": now,
            "priority": "normal",
            "is_featured": True,
        },
        {
            "title": "Nya rutiner för inventering",
            "type": "announcement",
            "content": "Vi har uppdaterat rutinerna för inventering i alla lager.",
            "created_by": admin_email,
            "created_at": now,
            "priority": "important",
            "is_featured": False,
        },
        {
            "title": "Systemunderhåll planerat",
            "type": "maintenance",
            "content": "Systemet kommer att vara otillgängligt söndag mellan 02:00 och 04:00.",
            "created_by": admin_email,
            "created_at": now,
            "priority": "normal",
            "is_featured": False,
        },
    ]
    for report in report_docs:
        db["reports"].update_one(
            {"title": report["title"]},
            {"$set": report},
            upsert=True,
        )

    settings_docs = [
        {"key": "company_name", "value": "Smart Lagring"},
        {"key": "currency", "value": "SEK"},
        {"key": "timezone", "value": "Europe/Stockholm"},
        {"key": "default_warehouse", "value": "WH-A"},
    ]
    for setting in settings_docs:
        db["settings"].update_one({"key": setting["key"]}, {"$set": setting}, upsert=True)

    db["audit_logs"].insert_one({
        "action": "seed_database",
        "actor_id": "system",
        "target_type": "project",
        "target_id": "inventory-manager",
        "details": {"message": "Initial seed data loaded for warehouse app"},
        "created_at": now,
    })

    return {
        "members": db["Medlem"].count_documents({}),
        "warehouses": db["warehouse"].count_documents({}),
        "materials": db["material"].count_documents({}),
        "deliveries": db["deliveries"].count_documents({}),
        "reports": db["reports"].count_documents({}),
        "settings": db["settings"].count_documents({}),
    }


if __name__ == "__main__":
    result = seed_database()
    print(result)
