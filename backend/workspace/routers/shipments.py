import os
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from ..database import connect_database
from ..models import ShipmentCreate, ShipmentStatusUpdate
from ..security import require_admin, require_authenticated

router = APIRouter(tags=["shipments"])


def serialize_shipment(shipment: dict[str, Any]) -> dict[str, Any]:
    created_at = shipment.get("created_at")
    if isinstance(created_at, datetime) and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return {
        "id": str(shipment["_id"]),
        "shipment_id": shipment.get("shipment_id", ""),
        "customer_name": shipment.get("customer_name", ""),
        "customer_email": shipment.get("customer_email", ""),
        "material_name": shipment.get("material_name", ""),
        "sku": shipment.get("sku", ""),
        "quantity": shipment.get("quantity", 0),
        "unit": shipment.get("unit", "st"),
        "warehouse": shipment.get("warehouse", "Okänt lager"),
        "status": shipment.get("status", "shipped"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else "",
    }


@router.get("/shipments")
async def list_shipments(_: dict[str, Any] = Depends(require_authenticated)) -> list[dict[str, Any]]:
    client, _ = connect_database()
    try:
        deliveries = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]["deliveries"]
        shipments = deliveries.find({"direction": "outgoing"}).sort("created_at", -1).limit(200)
        return [serialize_shipment(shipment) for shipment in shipments]
    finally:
        client.close()


@router.post("/shipments", status_code=201)
async def create_shipment(
    request: ShipmentCreate,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    client, _ = connect_database()
    try:
        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        try:
            material_id = ObjectId(request.material_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltig materialreferens.") from error

        materials = database["material"]
        stock = materials.find_one({"_id": material_id})
        if not stock:
            raise HTTPException(status_code=404, detail="Materialet finns inte längre i lagret.")

        warehouse = database["warehouse"].find_one({"_id": stock.get("warehouse_id")})
        if not warehouse:
            raise HTTPException(status_code=409, detail="Materialets lagerplats saknas.")

        damaged_count = int(stock.get("damaged_count", 0))
        available_quantity = int(stock.get("quantity", 0)) - damaged_count
        if request.quantity > available_quantity:
            raise HTTPException(status_code=409, detail=f"Endast {max(available_quantity, 0)} oskadade enheter finns tillgängliga.")

        now = datetime.now(timezone.utc)
        updated_stock = materials.find_one_and_update(
            {"_id": material_id, "quantity": {"$gte": request.quantity + damaged_count}},
            [
                {"$set": {"quantity": {"$subtract": ["$quantity", request.quantity]}, "updated_at": now}},
                {"$set": {"status": {"$cond": [{"$lte": ["$quantity", "$minimum_stock"]}, "low", "available"]}}},
            ],
            return_document=ReturnDocument.AFTER,
        )
        if not updated_stock:
            raise HTTPException(status_code=409, detail="Lagret ändrades. Uppdatera sidan och kontrollera saldot.")

        shipment = {
            "direction": "outgoing",
            "shipment_id": f"UTG-{uuid4().hex[:8].upper()}",
            "customer_name": request.customer_name.strip(),
            "customer_email": str(request.customer_email) if request.customer_email else "",
            "material_id": material_id,
            "material_name": stock.get("name", "Okänt material"),
            "sku": stock.get("sku", ""),
            "quantity": request.quantity,
            "unit": stock.get("unit", "st"),
            "warehouse_id": stock["warehouse_id"],
            "warehouse": warehouse.get("name", "Okänt lager"),
            "status": "shipped",
            "created_by": actor.get("sub", ""),
            "created_at": now,
        }
        try:
            result = database["deliveries"].insert_one(shipment)
        except Exception as error:
            materials.update_one(
                {"_id": material_id},
                [
                    {"$set": {"quantity": {"$add": ["$quantity", request.quantity]}, "updated_at": datetime.now(timezone.utc)}},
                    {"$set": {"status": {"$cond": [{"$lte": ["$quantity", "$minimum_stock"]}, "low", "available"]}}},
                ],
            )
            raise HTTPException(status_code=503, detail="Kunde inte spara leveransen. Lagret har återställts.") from error
        shipment["_id"] = result.inserted_id
        try:
            database["audit_logs"].insert_one({
                "action": "shipment_created",
                "actor_id": actor.get("sub", ""),
                "actor_role": actor.get("role", "Admin"),
                "target_type": "shipment",
                "target_id": shipment["shipment_id"],
                "details": {
                    "shipment_id": shipment["shipment_id"],
                    "customer_name": shipment["customer_name"],
                    "material_name": shipment["material_name"],
                    "sku": shipment["sku"],
                    "quantity": shipment["quantity"],
                    "unit": shipment["unit"],
                    "warehouse": shipment["warehouse"],
                },
                "created_at": now,
            })
        except Exception:
            logging.exception("Could not record shipment creation activity")
        return serialize_shipment(shipment)
    finally:
        client.close()


@router.patch("/shipments/{shipment_id}/status")
async def update_shipment_status(
    shipment_id: str,
    update: ShipmentStatusUpdate,
    actor: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    client, _ = connect_database()
    try:
        try:
            object_id = ObjectId(shipment_id)
        except Exception as error:
            raise HTTPException(status_code=400, detail="Ogiltigt leverans-ID.") from error

        database = client[os.getenv("MONGODB_DB_NAME", "inventory-manager")]
        deliveries = database["deliveries"]
        shipment = deliveries.find_one({"_id": object_id, "direction": "outgoing"})
        if not shipment:
            raise HTTPException(status_code=404, detail="Leveransen hittades inte.")
        if shipment.get("status") == update.status:
            return serialize_shipment(shipment)
        if shipment.get("status") != "shipped":
            raise HTTPException(status_code=409, detail="Endast skickade leveranser kan ändras.")

        now = datetime.now(timezone.utc)
        if update.status == "delivered":
            result = deliveries.update_one(
                {"_id": object_id, "status": "shipped"},
                {"$set": {"status": "delivered", "delivered_at": now, "updated_by": actor.get("sub", ""), "updated_at": now}},
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=409, detail="Leveransens status har redan ändrats.")
            activity_action = "shipment_delivered"
        else:
            result = deliveries.update_one(
                {"_id": object_id, "status": "shipped"},
                {"$set": {"status": "cancelled", "cancelled_at": now, "cancelled_by": actor.get("sub", ""), "updated_at": now}},
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=409, detail="Leveransens status har redan ändrats.")

            try:
                stock_result = database["material"].update_one(
                    {"_id": shipment.get("material_id")},
                    [
                        {"$set": {"quantity": {"$add": ["$quantity", shipment.get("quantity", 0)]}, "updated_at": now}},
                        {"$set": {"status": {"$cond": [{"$lte": ["$quantity", "$minimum_stock"]}, "low", "available"]}}},
                    ],
                )
                if stock_result.matched_count == 0:
                    raise RuntimeError("Source material was not found")
            except Exception as error:
                deliveries.update_one(
                    {"_id": object_id, "status": "cancelled"},
                    {"$set": {"status": "shipped"}, "$unset": {"cancelled_at": "", "cancelled_by": ""}},
                )
                raise HTTPException(status_code=503, detail="Kunde inte återföra varan. Leveransen är återställd till skickad.") from error
            activity_action = "shipment_cancelled"

        updated = deliveries.find_one({"_id": object_id})
        try:
            database["audit_logs"].insert_one({
                "action": activity_action,
                "actor_id": actor.get("sub", ""),
                "actor_role": actor.get("role", "Admin"),
                "target_type": "shipment",
                "target_id": updated.get("shipment_id", ""),
                "details": {
                    "shipment_id": updated.get("shipment_id", ""),
                    "customer_name": updated.get("customer_name", ""),
                    "material_name": updated.get("material_name", ""),
                    "sku": updated.get("sku", ""),
                    "quantity": updated.get("quantity", 0),
                    "unit": updated.get("unit", "st"),
                    "warehouse": updated.get("warehouse", "Okänt lager"),
                    "status": updated.get("status", ""),
                },
                "created_at": now,
            })
        except Exception:
            logging.exception("Could not record shipment status activity")
        return serialize_shipment(updated)
    finally:
        client.close()