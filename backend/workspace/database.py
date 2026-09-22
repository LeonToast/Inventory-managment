import os
from typing import Any

from fastapi import HTTPException

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None


def connect_database() -> tuple[Any, Any]:
    connection_string = os.getenv("MONGODB_URI")
    if not connection_string or MongoClient is None:
        raise HTTPException(status_code=503, detail="MongoDB is not configured")
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as error:
        client.close()
        raise HTTPException(status_code=503, detail="Could not connect to MongoDB") from error
    return client, client["inventory-manager"]["register-validering"]
