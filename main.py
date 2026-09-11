from fastapi import FastAPI
from inventory import router as inventory_router


app = FastAPI(
    title="Polar Expedition Inventory Service",
    description="Inventory management service for SIH 2026 PS 26062",
    version="1.0.0"
)


app.include_router(
    inventory_router,
    prefix="/inventory",
    tags=["Inventory"]
)


@app.get("/")
def home():
    return {
        "message": "Inventory Service is running"
    }