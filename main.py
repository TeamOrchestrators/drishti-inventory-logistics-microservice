from fastapi import FastAPI, HTTPException
from inventory_manager import InventoryManager

app = FastAPI()
manager = InventoryManager()

@app.get("/")
def home():
    return {"message": "Inventory Service is running"}

@app.get("/inventory")
def get_inventory():
    return manager.inventory

@app.get("/inventory/station/{station_id}")
def get_station_inventory(station_id: str):
    station_inventory = manager.get_station_inventory(station_id)

    if not station_inventory:
        raise HTTPException(
            status_code=404,
            detail="Station not found or no inventory available."
        )

    return station_inventory

@app.post("/inventory/{inventory_id}/add")
def add_stock(inventory_id: str, quantity: float):
    manager.add_stock(inventory_id, quantity)

    return {
        "message": "Stock added successfully",
        "inventory_id": inventory_id,
        "quantity_added": quantity
    }

@app.post("/inventory/{inventory_id}/remove")
def remove_stock(inventory_id: str, quantity: float):
    manager.remove_stock(inventory_id, quantity)

    return {
        "message": "Stock removed successfully",
        "inventory_id": inventory_id,
        "quantity_removed": quantity
    }

@app.put("/inventory/{inventory_id}")
def update_stock(inventory_id: str, new_quantity: float):
    manager.update_stock(inventory_id, new_quantity)

    return {
        "message": "Stock updated successfully",
        "inventory_id": inventory_id,
        "new_quantity": new_quantity
    }

@app.get("/inventory/history")
def get_history():
    return manager.history

@app.get("/inventory/{inventory_id}/consumption")
def get_consumption_history(inventory_id: str):
    consumption_history = manager.get_consumption_history(inventory_id)
    if not any(
        item["inventory_id"] == inventory_id
        for item in manager.inventory
    ):
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )
    return consumption_history

@app.get("/inventory/{inventory_id}/consumption/average")
def get_average_consumption(inventory_id: str):
    if not any(
        item["inventory_id"] == inventory_id
        for item in manager.inventory
    ):
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )
    average = manager.calculate_average_daily_consumption(
        inventory_id
    )
    return {
        "inventory_id": inventory_id,
        "average_daily_consumption": average
    }

@app.get("/inventory/{inventory_id}/stock-days")
def get_stock_days_remaining(inventory_id: str):
    item = next(
        (
            item for item in manager.inventory
            if item["inventory_id"] == inventory_id
        ),
        None
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )
    average = manager.calculate_average_daily_consumption(
        inventory_id
    )
    if average <= 0:
        return {
            "inventory_id": inventory_id,
            "current_quantity": item["current_quantity"],
            "average_daily_consumption": 0,
            "days_of_stock_remaining": None,
            "message": "Insufficient consumption history to calculate stock duration."
        }
    days = item["current_quantity"] / average
    return {
        "inventory_id": inventory_id,
        "current_quantity": item["current_quantity"],
        "average_daily_consumption": average,
        "days_of_stock_remaining": round(days, 2)
    }

@app.get("/inventory/{inventory_id}/depletion-date")
def get_predicted_depletion_date(inventory_id: str):
    item = next(
        (
            item for item in manager.inventory
            if item["inventory_id"] == inventory_id
        ),
        None
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found."
        )
    average = manager.calculate_average_daily_consumption(
        inventory_id
    )
    depletion_date = manager.calculate_predicted_depletion_date(
        inventory_id
    )
    if depletion_date is None:
        return {
            "inventory_id": inventory_id,
            "current_quantity": item["current_quantity"],
            "average_daily_consumption": average,
            "predicted_depletion_date": None,
            "message": "Insufficient consumption history to predict depletion date."
        }
    return {
        "inventory_id": inventory_id,
        "current_quantity": item["current_quantity"],
        "average_daily_consumption": average,
        "predicted_depletion_date": depletion_date
    }

@app.get("/inventory/alerts")
def get_alerts():
    alerts = []

    for item in manager.inventory:
        manager.update_status(item)

        if item["status"] == "Critical":
            alerts.append({
                "inventory_id": item["inventory_id"],
                "station_id": item["station_id"],
                "item_name": item["item_name"],
                "status": "Critical",
                "message": f"{item['item_name']} is critically low."
            })

        elif item["status"] == "Low":
            alerts.append({
                "inventory_id": item["inventory_id"],
                "station_id": item["station_id"],
                "item_name": item["item_name"],
                "status": "Low",
                "message": f"{item['item_name']} is running low."
            })

    return alerts