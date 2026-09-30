import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None


def connect_database() -> tuple[Any, Any]:
    connection_string = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DB_NAME", "inventory-manager")
    if not connection_string or MongoClient is None:
        raise HTTPException(status_code=503, detail="MongoDB is not configured")
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception as error:
        client.close()
        raise HTTPException(status_code=503, detail="Could not connect to MongoDB") from error
    return client, client[database_name]["register-validering"]
