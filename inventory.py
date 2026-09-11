from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class InventoryTransaction(BaseModel):
    transaction_type: str
    quantity_delta: float
    occurred_at: str


class StockDaysRequest(BaseModel):
    inventory_id: str
    current_quantity: float
    inventory_transactions: List[InventoryTransaction]


def calculate_stock_days(payload: StockDaysRequest):
    daily_consumption = get_daily_consumption(payload)

    total_consumption = sum(daily_consumption.values())
    number_of_days = len(daily_consumption)
    average_daily_consumption = (
        total_consumption / number_of_days
        if number_of_days
        else 0
    )
    stock_days = (
        payload.current_quantity / average_daily_consumption
        if average_daily_consumption
        else None
    )

    return {
        "inventory_id": payload.inventory_id,
        "current_quantity": payload.current_quantity,
        "average_daily_consumption": round(
            average_daily_consumption,
            2
        ),
        "days_of_stock_remaining": (
            round(stock_days, 2)
            if stock_days is not None
            else None
        )
    }


def get_daily_consumption(payload: StockDaysRequest):
    daily_consumption = defaultdict(float)

    for transaction in payload.inventory_transactions:
        if transaction.transaction_type != "consumption":
            continue

        if transaction.quantity_delta >= 0:
            continue

        try:
            date = datetime.fromisoformat(
                transaction.occurred_at.replace("Z", "+00:00")
            ).date().isoformat()
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=(
                    "occurred_at must be a valid ISO-8601 timestamp."
                )
            ) from error

        daily_consumption[date] += abs(transaction.quantity_delta)

    return daily_consumption


def get_average_consumption_value(payload: StockDaysRequest):
    daily_consumption = get_daily_consumption(payload)
    if not daily_consumption:
        return 0
    return sum(daily_consumption.values()) / len(daily_consumption)


def calculate_alerts(payload: StockDaysRequest):
    status = "Critical" if payload.current_quantity <= 0 else "Normal"
    return {
        "inventory_id": payload.inventory_id,
        "current_quantity": payload.current_quantity,
        "status": status,
        "alert": status == "Critical"
    }


def calculate_depletion_date(payload: StockDaysRequest):
    average = get_average_consumption_value(payload)
    if average <= 0:
        depletion_date = None
    else:
        days = payload.current_quantity / average
        depletion_date = (
            datetime.now(timezone.utc)
            + timedelta(days=days)
        ).date().isoformat()

    return {
        "inventory_id": payload.inventory_id,
        "predicted_depletion_date": depletion_date
    }


def calculate_anomalies(payload: StockDaysRequest):
    average = get_average_consumption_value(payload)
    anomalies = []

    if average > 0:
        for transaction in payload.inventory_transactions:
            consumption = abs(transaction.quantity_delta)
            if (
                transaction.transaction_type == "consumption"
                and consumption > average * 2
            ):
                anomalies.append(transaction.model_dump())

    return {
        "inventory_id": payload.inventory_id,
        "anomaly_detected": bool(anomalies),
        "anomalies": anomalies
    }


def unsupported_backend_operation(operation: str):
    raise HTTPException(
        status_code=501,
        detail=(
            operation
            + " requires a request-body contract from the backend."
        )
    )


def get_backend_inventory(path: str):
    return unsupported_backend_operation(
        "This endpoint"
    )


def request_backend(method: str, path: str, payload=None):
    return unsupported_backend_operation(
        "This endpoint"
    )


def query_payload(
    inventory_id: str,
    current_quantity: float
):
    return StockDaysRequest(
        inventory_id=inventory_id,
        current_quantity=current_quantity,
        inventory_transactions=[]
    )

@router.get("/")
def get_inventory():
    raise HTTPException(
        status_code=405,
        detail="Send inventory data in a POST request to an analytics endpoint."
    )

@router.get("/station/{station_id}")
def get_station_inventory(station_id: str):
    return get_backend_inventory(
        "/api/stations/" + station_id + "/inventory"
    )

@router.post("/alerts")
def get_alerts(payload: StockDaysRequest):
    return calculate_alerts(payload)


@router.get("/alerts")
def get_alerts_compatibility(
    inventory_id: str = Query("unknown"),
    current_quantity: float = Query(0)
):
    return calculate_alerts(
        query_payload(inventory_id, current_quantity)
    )

@router.get("/history")
def get_history():
    return unsupported_backend_operation("Inventory history")

@router.get("/compare")
def compare_item_across_stations():
    return unsupported_backend_operation("Cross-station comparison")

@router.post("/{inventory_id}/add")
def add_stock(
    inventory_id: str,
    station_id: str,
    quantity: float
):
    return request_backend(
        "POST",
        "/api/stations/"
        + station_id
        + "/inventory/"
        + inventory_id
        + "/stock",
        {"quantity_delta": quantity}
    )

@router.post("/{inventory_id}/remove")
def remove_stock(
    inventory_id: str,
    station_id: str,
    quantity: float
):
    return request_backend(
        "POST",
        "/api/stations/"
        + station_id
        + "/inventory/"
        + inventory_id
        + "/stock",
        {"quantity_delta": -quantity}
    )

@router.put("/{inventory_id}")
def update_stock(
    inventory_id: str,
    station_id: str,
    new_quantity: float
):
    return request_backend(
        "POST",
        "/api/stations/"
        + station_id
        + "/inventory/"
        + inventory_id
        + "/stock",
        {"new_quantity": new_quantity}
    )

@router.post("/consumption")
def get_consumption_history(payload: StockDaysRequest):
    return [
        transaction.model_dump()
        for transaction in payload.inventory_transactions
    ]

@router.post("/consumption/average")
def get_average_consumption(payload: StockDaysRequest):
    return {
        "inventory_id": payload.inventory_id,
        "average_daily_consumption": round(
            get_average_consumption_value(payload),
            2
        )
    }


@router.get("/consumption/average")
def get_average_consumption_compatibility(
    inventory_id: str = Query("unknown"),
    current_quantity: float = Query(0)
):
    payload = query_payload(inventory_id, current_quantity)
    return {
        "inventory_id": payload.inventory_id,
        "average_daily_consumption": 0
    }


@router.post("/stock-days")
def get_stock_days_remaining(
    payload: StockDaysRequest
):
    return calculate_stock_days(payload)

@router.post("/depletion-date")
def get_predicted_depletion_date(payload: StockDaysRequest):
    return calculate_depletion_date(payload)


@router.get("/depletion-date")
def get_predicted_depletion_date_compatibility(
    inventory_id: str = Query("unknown"),
    current_quantity: float = Query(0)
):
    return calculate_depletion_date(
        query_payload(inventory_id, current_quantity)
    )

@router.post("/anomalies")
def get_inventory_anomalies(payload: StockDaysRequest):
    return calculate_anomalies(payload)


@router.get("/anomalies")
def get_inventory_anomalies_compatibility(
    inventory_id: str = Query("unknown"),
    current_quantity: float = Query(0)
):
    return calculate_anomalies(
        query_payload(inventory_id, current_quantity)
    )

@router.get("/forecast")
def get_demand_forecast(
    forecast_days: int = 7
):
    if forecast_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="Forecast days must be greater than 0."
        )
    return unsupported_backend_operation(
        "Demand forecasting"
    )

@router.get("/trend")
def get_consumption_trend():
    return unsupported_backend_operation("Consumption trend")

@router.get(
    "/simulate/shipment-delay"
)
def simulate_shipment_delay(
    delay_days: int
):
    if delay_days < 0:
        raise HTTPException(
            status_code=400,
            detail="Delay days cannot be negative."
        )
    return unsupported_backend_operation(
        "Shipment-delay simulation"
    )

@router.get(
    "/simulate/consumption-increase"
)
def simulate_consumption_increase(
    increase_percentage: float
):
    if increase_percentage < 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Increase percentage "
                "cannot be negative."
            )
        )
    return unsupported_backend_operation(
        "Consumption-increase simulation"
    )
