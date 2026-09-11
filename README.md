# Polar Expedition Inventory Service

Inventory management microservice for **SIH 2026 – PS 26062: Integrated Polar Expedition Logistics and Asset Management System**.

This service manages station-wise inventory, stock movements, consumption analysis, forecasting, alerts, and inventory risk monitoring for polar expedition operations.

## Features

### Core Inventory Management
- Station-wise inventory
- Add stock
- Remove / consume stock
- Update / adjust stock
- Current quantity tracking
- Minimum required quantity
- Maximum storage capacity
- Item criticality
- Inventory transaction history

### Consumption & Analysis
- Consumption history
- Average daily consumption
- Days of stock remaining
- Predicted depletion date
- Consumption trend analysis
- Forecasted demand

### Alerts & Risk Monitoring
- Low-stock alerts
- Critical-stock alerts
- Consumption anomaly detection
- Shipment-delay simulation
- Consumption-increase simulation

### Comparison
- Compare the same inventory item across available stations

## Tech Stack

- **Python**
- **FastAPI**
- **Uvicorn**
- **JSON** for prototype data storage
- **Pydantic** for request validation
- **Git & GitHub**

## Project Structure

```text
SIH26/
│
├── Inventory/
│   ├── inventory.py
│   ├── inventory_manager.py
│   ├── inventory.json
│   ├── main.py
│   ├── .gitignore
│   └── README.md
│
└── README.md
