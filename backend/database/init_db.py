from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database


def initialize_database(db: Database) -> None:
    """Create the collections and indexes required by this project."""
    indexes: dict[str, list[dict[str, object]]] = {
        "Medlem": [
            {"key": [("email", ASCENDING)], "unique": True, "sparse": True},
            {"key": [("role", ASCENDING)]},
            {"key": [("created_at", DESCENDING)]},
        ],
        "register-validering": [
            {"key": [("status", ASCENDING), ("submitted_at", DESCENDING)]},
            {"key": [("email", ASCENDING)]},
        ],
        "warehouse": [
            {"key": [("name", ASCENDING)], "unique": True},
            {"key": [("code", ASCENDING)], "unique": True},
        ],
        "material": [
            {"key": [("warehouse_id", ASCENDING), ("sku", ASCENDING)]},
            {"key": [("category", ASCENDING)]},
            {"key": [("status", ASCENDING)]},
        ],
        "deliveries": [
            {"key": [("status", ASCENDING), ("scheduled_at", DESCENDING)]},
            {"key": [("warehouse_id", ASCENDING)]},
            {"key": [("supplier", ASCENDING)]},
        ],
        "reports": [
            {"key": [("created_at", DESCENDING)]},
            {"key": [("type", ASCENDING)]},
        ],
        "audit_logs": [
            {"key": [("created_at", DESCENDING)]},
            {"key": [("actor_id", ASCENDING)]},
        ],
        "settings": [
            {"key": [("key", ASCENDING)], "unique": True},
        ],
    }

    for collection_name, specs in indexes.items():
        collection = db[collection_name]
        for spec in specs:
            collection.create_index(spec["key"], **{k: v for k, v in spec.items() if k != "key"})


def seed_default_admin(db: Database) -> None:
    """Create the default admin account if it doesn't already exist."""
    members = db["Medlem"]
    if members.count_documents({"email": "admin@dev.local"}, limit=1) == 0:
        members.insert_one({
            "name": "Admin",
            "email": "admin@dev.local",
            "password_hash": "$argon2$",
            "role": "Admin",
            "is_active": True,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        })


__all__ = ["initialize_database", "seed_default_admin"]
