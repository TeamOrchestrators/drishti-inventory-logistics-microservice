import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


class InventoryManager:
    def __init__(self):
        self.data = {}
        self.stations = []
        self.items = []
        self.inventory = []
        self.transactions = []
        self.inventory_id_aliases = {}
        self.data_file = Path(__file__).resolve().parent / "inventory.json"
        self.load_data()

    def load_data(self):
        with self.data_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        self.data = data

        self.stations = data["stations"]
        self.items = data["items"]
        self.inventory = data["station_inventory"]
        self.transactions = data["inventory_transactions"]
        self.inventory_id_aliases = data.get(
            "inventory_id_aliases",
            {}
        )

        # Keep available quantity consistent with on-hand
        # and reserved quantities.
        for item in self.inventory:
            self.update_available_quantity(item)

    def save_data(self):
        # Update only the inventory-related sections.
        # All other sections in inventory.json are preserved.
        self.data["stations"] = self.stations
        self.data["items"] = self.items
        self.data["station_inventory"] = self.inventory
        self.data["inventory_transactions"] = self.transactions

        with self.data_file.open("w", encoding="utf-8") as file:
            json.dump(
                self.data,
                file,
                indent=2
            )

    def get_item(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                return item
        return None

    def get_station(self, station_id):
        for station in self.stations:
            if station["id"] == station_id:
                return station
        return None

    def get_inventory_item(self, inventory_id):
        inventory_id = self.resolve_inventory_id(inventory_id)

        for item in self.inventory:
            if item["id"] == inventory_id:
                return item
        return None

    def resolve_inventory_id(self, inventory_id):
        if any(
            item["id"] == inventory_id
            for item in self.inventory
        ):
            return inventory_id

        return self.inventory_id_aliases.get(
            inventory_id,
            inventory_id
        )

    def get_item_name(self, item_id):
        item = self.get_item(item_id)
        return item["name"] if item else "Unknown Item"

    def get_item_unit(self, item_id):
        item = self.get_item(item_id)
        return item["unit"] if item else ""

    def get_station_name(self, station_id):
        station = self.get_station(station_id)
        return station["name"] if station else "Unknown Station"

    def update_available_quantity(self, item):
        item["available_quantity"] = (
            item["on_hand_quantity"]
            - item["reserved_quantity"]
        )

    def update_status(self, item):
        available = item["available_quantity"]
        minimum = item["minimum_quantity"]

        if available <= minimum:
            return "Critical"
        elif available <= minimum * 1.5:
            return "Low"

        return "Normal"

    def view_inventory(self):
        if not self.inventory:
            print("No inventory available.")
            return

        for item in self.inventory:
            item_name = self.get_item_name(item["item_id"])
            unit = self.get_item_unit(item["item_id"])
            station_name = self.get_station_name(item["station_id"])
            status = self.update_status(item)

            print(
                f"ID: {item['id']} | "
                f"Station: {station_name} | "
                f"Item: {item_name} | "
                f"On Hand: {item['on_hand_quantity']} {unit} | "
                f"Reserved: {item['reserved_quantity']} {unit} | "
                f"Available: {item['available_quantity']} {unit} | "
                f"Status: {status}"
            )

    def get_station_inventory(self, station_id):
        station_inventory = []

        for item in self.inventory:
            if item["station_id"] == station_id:
                station_inventory.append(item)

        return station_inventory

    def compare_item_across_stations(self, item_id):
        item = self.get_item(item_id)

        if not item:
            return None

        comparison = []

        for inventory_item in self.inventory:
            if inventory_item["item_id"] != item_id:
                continue

            station = self.get_station(
                inventory_item["station_id"]
            )

            comparison.append({
                "station_id": inventory_item["station_id"],
                "station_name": (
                    station["name"]
                    if station
                    else "Unknown Station"
                ),
                "item_id": item_id,
                "item_name": item["name"],
                "unit": item["unit"],
                "on_hand_quantity": (
                    inventory_item["on_hand_quantity"]
                ),
                "reserved_quantity": (
                    inventory_item["reserved_quantity"]
                ),
                "available_quantity": (
                    inventory_item["available_quantity"]
                ),
                "minimum_quantity": (
                    inventory_item["minimum_quantity"]
                ),
                "maximum_quantity": (
                    inventory_item["maximum_quantity"]
                ),
                "status": self.update_status(inventory_item)
            })

        return comparison

    def add_transaction(
        self,
        inventory_id,
        transaction_type,
        on_hand_delta,
        reserved_delta=0,
        reference_type=None,
        reference_id=None,
        notes=None
    ):
        transaction = {
            "id": f"TX-{len(self.transactions) + 1:03d}",
            "station_inventory_id": inventory_id,
            "transaction_type": transaction_type,
            "on_hand_delta": on_hand_delta,
            "reserved_delta": reserved_delta,
            "occurred_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "reference_type": reference_type,
            "reference_id": reference_id,
            "notes": notes
        }

        self.transactions.append(transaction)

        return transaction

    def add_stock(self, inventory_id, quantity):
        inventory_id = self.resolve_inventory_id(inventory_id)
        item = self.get_inventory_item(inventory_id)

        if not item:
            raise ValueError("Inventory item not found.")

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than 0."
            )

        new_quantity = (
            item["on_hand_quantity"] + quantity
        )

        if (
            item["maximum_quantity"] is not None
            and new_quantity > item["maximum_quantity"]
        ):
            raise ValueError(
                "Cannot add stock. Maximum quantity exceeded."
            )

        previous_quantity = item["on_hand_quantity"]

        item["on_hand_quantity"] = new_quantity

        self.update_available_quantity(item)

        self.add_transaction(
            inventory_id=inventory_id,
            transaction_type="receipt",
            on_hand_delta=quantity,
            notes="Stock received."
        )

        self.save_data()

        print(
            f"{quantity} "
            f"{self.get_item_unit(item['item_id'])} "
            f"of "
            f"{self.get_item_name(item['item_id'])} "
            f"added successfully."
        )

        print(
            f"Previous quantity: {previous_quantity}"
        )

        print(
            f"New on-hand quantity: "
            f"{item['on_hand_quantity']}"
        )

        return item

    def remove_stock(self, inventory_id, quantity):
        inventory_id = self.resolve_inventory_id(inventory_id)
        item = self.get_inventory_item(inventory_id)

        if not item:
            raise ValueError(
                "Inventory item not found."
            )

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than 0."
            )

        if quantity > item["available_quantity"]:
            raise ValueError(
                "Cannot consume stock. "
                "Insufficient available quantity."
            )

        previous_quantity = item["on_hand_quantity"]

        item["on_hand_quantity"] -= quantity

        self.update_available_quantity(item)

        self.add_transaction(
            inventory_id=inventory_id,
            transaction_type="consumption",
            on_hand_delta=-quantity,
            reserved_delta=0,
            notes="Stock consumed."
        )

        self.save_data()

        print(
            f"{quantity} "
            f"{self.get_item_unit(item['item_id'])} "
            f"of "
            f"{self.get_item_name(item['item_id'])} "
            f"consumed successfully."
        )

        print(
            f"Previous quantity: {previous_quantity}"
        )

        print(
            f"Remaining on-hand quantity: "
            f"{item['on_hand_quantity']}"
        )

        return item

    def update_stock(self, inventory_id, new_quantity):
        inventory_id = self.resolve_inventory_id(inventory_id)
        item = self.get_inventory_item(inventory_id)

        if not item:
            raise ValueError(
                "Inventory item not found."
            )

        if new_quantity < 0:
            raise ValueError(
                "Quantity cannot be negative."
            )

        if (
            item["maximum_quantity"] is not None
            and new_quantity > item["maximum_quantity"]
        ):
            raise ValueError(
                "Cannot update stock. "
                "Maximum quantity exceeded."
            )

        if new_quantity < item["reserved_quantity"]:
            raise ValueError(
                "Cannot update stock below "
                "the reserved quantity."
            )

        previous_quantity = item["on_hand_quantity"]

        item["on_hand_quantity"] = new_quantity

        self.update_available_quantity(item)

        self.add_transaction(
            inventory_id=inventory_id,
            transaction_type="adjustment",
            on_hand_delta=(
                new_quantity - previous_quantity
            ),
            reserved_delta=0,
            notes="Inventory quantity adjusted."
        )

        self.save_data()

        print(
            f"{self.get_item_name(item['item_id'])} "
            f"quantity updated successfully."
        )

        print(
            f"New on-hand quantity: "
            f"{item['on_hand_quantity']}"
        )

        return item

    def view_history(self):
        if not self.transactions:
            print(
                "No inventory transactions available."
            )
            return

        for record in self.transactions:
            item = self.get_inventory_item(
                record["station_inventory_id"]
            )

            item_name = (
                self.get_item_name(item["item_id"])
                if item
                else "Unknown Item"
            )

            print(
                f"Transaction ID: {record['id']} | "
                f"Item: {item_name} | "
                f"Type: {record['transaction_type']} | "
                f"On-hand change: "
                f"{record['on_hand_delta']} | "
                f"Reserved change: "
                f"{record['reserved_delta']} | "
                f"Time: "
                f"{record.get('occurred_at', 'N/A')}"
            )

    def get_consumption_history(self, inventory_id):
        inventory_id = self.resolve_inventory_id(inventory_id)
        consumption_history = []

        for record in self.transactions:
            if (
                record["station_inventory_id"]
                == inventory_id
                and record["transaction_type"]
                == "consumption"
            ):
                consumption_history.append(record)

        return consumption_history

    def get_daily_consumption(self, inventory_id):
        consumption_history = (
            self.get_consumption_history(
                inventory_id
            )
        )

        daily_consumption = {}

        for record in consumption_history:
            occurred_at = record.get("occurred_at")

            if not occurred_at:
                continue

            date = occurred_at[:10]

            consumption = abs(
                record["on_hand_delta"]
            )

            if date not in daily_consumption:
                daily_consumption[date] = 0

            daily_consumption[date] += consumption

        return daily_consumption

    def prepare_consumption_time_series(
        self,
        inventory_id
    ):
        daily_consumption = (
            self.get_daily_consumption(
                inventory_id
            )
        )

        if not daily_consumption:
            return []

        dates = sorted(
            daily_consumption.keys()
        )

        start_date = datetime.fromisoformat(
            dates[0]
        ).date()

        end_date = datetime.fromisoformat(
            dates[-1]
        ).date()

        time_series = []

        current_date = start_date

        while current_date <= end_date:
            date_string = (
                current_date.isoformat()
            )

            time_series.append({
                "date": date_string,
                "consumption": (
                    daily_consumption.get(
                        date_string,
                        0
                    )
                )
            })

            current_date += timedelta(days=1)

        return time_series

    def get_forecasting_data(self, inventory_id):
        time_series = (
            self.prepare_consumption_time_series(
                inventory_id
            )
        )

        if len(time_series) < 7:
            return {
                "ready": False,
                "data_points": len(time_series),
                "message": (
                    "Insufficient historical data "
                    "for demand forecasting. "
                    "At least 7 days of consumption "
                    "history are recommended."
                )
            }

        return {
            "ready": True,
            "data_points": len(time_series),
            "time_series": time_series
        }

    def forecast_demand(
        self,
        inventory_id,
        forecast_days=7
    ):
        if forecast_days <= 0:
            return {
                "error": (
                    "Forecast days must be "
                    "greater than 0."
                )
            }

        forecasting_data = (
            self.get_forecasting_data(
                inventory_id
            )
        )

        if not forecasting_data["ready"]:
            return forecasting_data

        time_series = (
            forecasting_data["time_series"]
        )

        consumption_values = [
            record["consumption"]
            for record in time_series
        ]

        recent_days = min(
            7,
            len(consumption_values)
        )

        recent_consumption = (
            consumption_values[-recent_days:]
        )

        average_daily_demand = (
            sum(recent_consumption)
            / recent_days
        )

        trend_data = (
            self.calculate_consumption_trend(
                inventory_id
            )
        )

        trend = trend_data.get("trend")

        if trend == "Increasing":
            adjusted_daily_demand = (
                average_daily_demand * 1.10
            )
        elif trend == "Decreasing":
            adjusted_daily_demand = (
                average_daily_demand * 0.90
            )
        else:
            adjusted_daily_demand = (
                average_daily_demand
            )

        predicted_demand = (
            adjusted_daily_demand
            * forecast_days
        )

        confidence_data = (
            self.calculate_forecast_confidence(
                inventory_id
            )
        )

        confidence = confidence_data[
            "confidence"
        ]

        return {
            "inventory_id": inventory_id,
            "historical_data_points": (
                len(time_series)
            ),
            "forecast_days": forecast_days,
            "average_daily_demand": round(
                average_daily_demand,
                2
            ),
            "trend": trend,
            "adjusted_daily_demand": round(
                adjusted_daily_demand,
                2
            ),
            "predicted_demand": round(
                predicted_demand,
                2
            ),
            "confidence": confidence
        }

    def calculate_consumption_trend(
        self,
        inventory_id
    ):
        time_series = (
            self.prepare_consumption_time_series(
                inventory_id
            )
        )

        if len(time_series) < 4:
            return {
                "inventory_id": inventory_id,
                "trend": "Unknown",
                "message": (
                    "Insufficient historical data "
                    "to determine consumption trend."
                )
            }

        consumption_values = [
            record["consumption"]
            for record in time_series
        ]

        midpoint = (
            len(consumption_values) // 2
        )

        first_half = (
            consumption_values[:midpoint]
        )

        second_half = (
            consumption_values[midpoint:]
        )

        first_average = (
            sum(first_half)
            / len(first_half)
        )

        second_average = (
            sum(second_half)
            / len(second_half)
        )

        if first_average == 0:
            if second_average > 0:
                trend = "Increasing"
            else:
                trend = "Stable"
        else:
            percentage_change = (
                (
                    second_average
                    - first_average
                )
                / first_average
            ) * 100

            if percentage_change > 10:
                trend = "Increasing"
            elif percentage_change < -10:
                trend = "Decreasing"
            else:
                trend = "Stable"

        return {
            "inventory_id": inventory_id,
            "trend": trend,
            "first_period_average": round(
                first_average,
                2
            ),
            "second_period_average": round(
                second_average,
                2
            )
        }

    def calculate_forecast_confidence(
        self,
        inventory_id
    ):
        time_series = (
            self.prepare_consumption_time_series(
                inventory_id
            )
        )

        data_points = len(time_series)

        if data_points < 7:
            confidence = "Low"
        elif data_points < 30:
            confidence = "Medium"
        else:
            confidence = "High"

        return {
            "inventory_id": inventory_id,
            "historical_data_points": (
                data_points
            ),
            "confidence": confidence
        }

    def calculate_average_daily_consumption(
        self,
        inventory_id
    ):
        consumption_history = (
            self.get_consumption_history(
                inventory_id
            )
        )

        if not consumption_history:
            return 0

        total_consumption = sum(
            abs(record["on_hand_delta"])
            for record in consumption_history
        )

        dates = []

        for record in consumption_history:
            timestamp = record.get(
                "occurred_at"
            )

            if timestamp:
                dates.append(
                    timestamp[:10]
                )

        unique_dates = set(dates)

        if not unique_dates:
            return 0

        return (
            total_consumption
            / len(unique_dates)
        )

    def calculate_days_of_stock_remaining(
        self,
        inventory_id
    ):
        item = self.get_inventory_item(
            inventory_id
        )

        if not item:
            return None

        average_consumption = (
            self.calculate_average_daily_consumption(
                inventory_id
            )
        )

        if average_consumption <= 0:
            return None

        return (
            item["available_quantity"]
            / average_consumption
        )

    def calculate_predicted_depletion_date(
        self,
        inventory_id
    ):
        item = self.get_inventory_item(
            inventory_id
        )

        if not item:
            return None

        average_consumption = (
            self.calculate_average_daily_consumption(
                inventory_id
            )
        )

        if average_consumption <= 0:
            return None

        days_remaining = (
            item["available_quantity"]
            / average_consumption
        )

        depletion_date = (
            datetime.now(timezone.utc)
            + timedelta(days=days_remaining)
        )

        return depletion_date.date().isoformat()

    def simulate_shipment_delay(
        self,
        inventory_id,
        delay_days
    ):
        item = self.get_inventory_item(
            inventory_id
        )

        if not item:
            return None

        if delay_days < 0:
            return {
                "error": (
                    "Delay days cannot be negative."
                )
            }

        average_consumption = (
            self.calculate_average_daily_consumption(
                inventory_id
            )
        )

        if average_consumption <= 0:
            return {
                "inventory_id": inventory_id,
                "item_name": self.get_item_name(
                    item["item_id"]
                ),
                "message": (
                    "Insufficient consumption "
                    "history to simulate "
                    "shipment delay."
                )
            }

        available_quantity = (
            item["available_quantity"]
        )

        projected_consumption = (
            average_consumption * delay_days
        )

        projected_quantity = (
            available_quantity
            - projected_consumption
        )

        minimum_quantity = (
            item["minimum_quantity"]
        )

        if projected_quantity <= 0:
            risk = "Critical"
            message = (
                "Stock may be depleted "
                "during the shipment delay."
            )
        elif projected_quantity <= minimum_quantity:
            risk = "High"
            message = (
                "Stock may fall below the "
                "minimum required quantity."
            )
        else:
            risk = "Low"
            message = (
                "Stock is expected to remain "
                "above the minimum level."
            )

        return {
            "inventory_id": inventory_id,
            "item_name": self.get_item_name(
                item["item_id"]
            ),
            "unit": self.get_item_unit(
                item["item_id"]
            ),
            "current_available_quantity": (
                available_quantity
            ),
            "average_daily_consumption": round(
                average_consumption,
                2
            ),
            "delay_days": delay_days,
            "projected_consumption": round(
                projected_consumption,
                2
            ),
            "projected_remaining_quantity": round(
                max(projected_quantity, 0),
                2
            ),
            "minimum_quantity": minimum_quantity,
            "risk": risk,
            "message": message
        }

    def simulate_consumption_increase(
        self,
        inventory_id,
        increase_percentage
    ):
        item = self.get_inventory_item(
            inventory_id
        )

        if not item:
            return None

        if increase_percentage < 0:
            return {
                "error": (
                    "Increase percentage "
                    "cannot be negative."
                )
            }

        average_consumption = (
            self.calculate_average_daily_consumption(
                inventory_id
            )
        )

        if average_consumption <= 0:
            return {
                "inventory_id": inventory_id,
                "item_name": self.get_item_name(
                    item["item_id"]
                ),
                "message": (
                    "Insufficient consumption "
                    "history to simulate "
                    "increased consumption."
                )
            }

        increase_factor = (
            1 + (increase_percentage / 100)
        )

        new_daily_consumption = (
            average_consumption
            * increase_factor
        )

        available_quantity = (
            item["available_quantity"]
        )

        days_remaining = (
            available_quantity
            / new_daily_consumption
        )

        minimum_quantity = (
            item["minimum_quantity"]
        )

        projected_quantity_after_7_days = (
            available_quantity
            - (new_daily_consumption * 7)
        )

        if projected_quantity_after_7_days <= 0:
            risk = "Critical"
            message = (
                "Stock may be depleted "
                "within 7 days."
            )
        elif (
            projected_quantity_after_7_days
            <= minimum_quantity
        ):
            risk = "High"
            message = (
                "Stock may fall below the "
                "minimum required quantity "
                "within 7 days."
            )
        else:
            risk = "Low"
            message = (
                "Stock is expected to remain "
                "above the minimum level "
                "for the next 7 days."
            )

        return {
            "inventory_id": inventory_id,
            "item_name": self.get_item_name(
                item["item_id"]
            ),
            "unit": self.get_item_unit(
                item["item_id"]
            ),
            "current_available_quantity": (
                available_quantity
            ),
            "current_average_daily_consumption": (
                round(
                    average_consumption,
                    2
                )
            ),
            "increase_percentage": (
                increase_percentage
            ),
            "new_daily_consumption": round(
                new_daily_consumption,
                2
            ),
            "days_of_stock_remaining": round(
                days_remaining,
                2
            ),
            "projected_quantity_after_7_days": (
                round(
                    max(
                        projected_quantity_after_7_days,
                        0
                    ),
                    2
                )
            ),
            "minimum_quantity": (
                minimum_quantity
            ),
            "risk": risk,
            "message": message
        }

    def detect_anomalies(self, inventory_id):
        item = self.get_inventory_item(
            inventory_id
        )

        if not item:
            return None

        consumption_history = (
            self.get_consumption_history(
                inventory_id
            )
        )

        if len(consumption_history) < 2:
            return {
                "inventory_id": inventory_id,
                "anomaly_detected": False,
                "message": (
                    "Insufficient consumption "
                    "history to detect anomalies."
                )
            }

        average_consumption = (
            self.calculate_average_daily_consumption(
                inventory_id
            )
        )

        if average_consumption <= 0:
            return {
                "inventory_id": inventory_id,
                "anomaly_detected": False,
                "message": (
                    "Insufficient consumption "
                    "data to detect anomalies."
                )
            }

        anomalies = []

        for transaction in consumption_history:
            consumption = abs(
                transaction["on_hand_delta"]
            )

            if (
                consumption
                > average_consumption * 2
            ):
                anomalies.append({
                    "transaction_id": (
                        transaction["id"]
                    ),
                    "consumption": consumption,
                    "average_consumption": round(
                        average_consumption,
                        2
                    ),
                    "occurred_at": (
                        transaction.get(
                            "occurred_at"
                        )
                    ),
                    "message": (
                        "Unusually high "
                        "consumption detected."
                    )
                })

        return {
            "inventory_id": inventory_id,
            "item_name": self.get_item_name(
                item["item_id"]
            ),
            "anomaly_detected": (
                len(anomalies) > 0
            ),
            "anomalies": anomalies
        }

    def check_alerts(self):
        alerts = []

        for item in self.inventory:
            status = self.update_status(item)

            if status == "Critical":
                alerts.append({
                    "inventory_id": item["id"],
                    "station_id": item["station_id"],
                    "item_id": item["item_id"],
                    "item_name": self.get_item_name(
                        item["item_id"]
                    ),
                    "status": "Critical",
                    "available_quantity": (
                        item["available_quantity"]
                    ),
                    "minimum_quantity": (
                        item["minimum_quantity"]
                    ),
                    "message": (
                        f"{self.get_item_name(item['item_id'])} "
                        f"is critically low."
                    )
                })

            elif status == "Low":
                alerts.append({
                    "inventory_id": item["id"],
                    "station_id": item["station_id"],
                    "item_id": item["item_id"],
                    "item_name": self.get_item_name(
                        item["item_id"]
                    ),
                    "status": "Low",
                    "available_quantity": (
                        item["available_quantity"]
                    ),
                    "minimum_quantity": (
                        item["minimum_quantity"]
                    ),
                    "message": (
                        f"{self.get_item_name(item['item_id'])} "
                        f"is running low."
                    )
                })

        return alerts