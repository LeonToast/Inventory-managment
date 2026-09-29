import os
from functools import lru_cache
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None


@lru_cache(maxsize=1)
def get_client() -> Any:
    """Return the shared, pooled MongoClient. A failed connect is not cached, so it retries."""
    connection_string = os.getenv("MONGODB_URI")
    if not connection_string or MongoClient is None:
        raise HTTPException(status_code=503, detail="MongoDB is not configured")
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as error:
        client.close()
        raise HTTPException(status_code=503, detail="Could not connect to MongoDB") from error
    return client


def applications_collection() -> Any:
    return get_client()["inventory-manager"]["register-validering"]


def members_collection() -> Any:
    return get_client()["inventory-manager"]["Medlem"]


@lru_cache(maxsize=1)
def reports_collection() -> Any:
    reports = get_client()["components"]["rapport"]
    reports.create_index("serial_number", unique=True, partialFilterExpression={"kind": "damage"})
    return reports


def materials_collection() -> Any:
    return get_client()["components"]["Materiel"]


def activity_collection() -> Any:
    return get_client()["components"]["Senaste"]


def announcements_collection() -> Any:
    return get_client()["inventory-manager"]["Meddelande"]


def parse_object_id(value: str, detail: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as error:
        raise HTTPException(status_code=400, detail=detail) from error
