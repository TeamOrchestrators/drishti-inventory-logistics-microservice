import json
from datetime import datetime, timezone, timedelta

class InventoryManager:
    def __init__(self):
        self.history = []
        self.inventory = []
        self.load_data()

    def load_data(self):
        with open("inventory.json", "r") as file:
            data = json.load(file)

        self.inventory = data["inventory"]
        self.history = data["history"]

    def save_data(self):
        with open("inventory.json", "w") as file:
            json.dump(
                {
                    "inventory": self.inventory,
                    "history": self.history
                },
                file,
                indent=2
            )

    def add_history(self, inventory_id, action, quantity, previous_quantity, new_quantity):
        record = {
            "inventory_id": inventory_id,
            "action": action,
            "quantity": quantity,
            "previous_quantity": previous_quantity,
            "new_quantity": new_quantity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.history.append(record)

    def view_inventory(self):
        for item in self.inventory:
            print(
                f"ID: {item['inventory_id']} | "
                f"Station: {item['station_id']} | "
                f"Item: {item['item_name']} | "
                f"Quantity: {item['current_quantity']} {item['unit']} | "
                f"Status: {item['status']}"
            )

    def get_station_inventory(self, station_id):
        station_inventory = []
        for item in self.inventory:
            if item["station_id"] == station_id:
                station_inventory.append(item)
        return station_inventory

    def add_stock(self, inventory_id, quantity):
        for item in self.inventory:
            if item["inventory_id"] == inventory_id:
                if quantity <= 0:
                    print("Quantity must be greater than 0.")
                    return
                new_quantity = item["current_quantity"] + quantity

                if new_quantity > item["maximum_capacity"]:
                    print("Cannot add stock. Maximum capacity exceeded.")
                    return

                previous_quantity = item["current_quantity"]
                item["current_quantity"] = new_quantity
                item["last_updated"] = datetime.now(timezone.utc).isoformat()
                self.update_status(item)
                self.add_history(
                    inventory_id,
                    "ADD",
                    quantity,
                    previous_quantity,
                    new_quantity
                )
                self.save_data()
                print(
                    f"{quantity} {item['unit']} of {item['item_name']} added successfully."
                )
                print(f"New quantity: {item['current_quantity']} {item['unit']}")
                return
        print("Inventory item not found.")

    def remove_stock(self, inventory_id, quantity):
        for item in self.inventory:
            if item["inventory_id"] == inventory_id:
                if quantity <= 0:
                    print("Quantity must be greater than 0.")
                    return
                if quantity > item["current_quantity"]:
                    print("Cannot remove stock. Insufficient quantity.")
                    return
                
                previous_quantity = item["current_quantity"]
                item["current_quantity"] -= quantity
                new_quantity = item["current_quantity"]
                item["last_updated"] = datetime.now(timezone.utc).isoformat()
                self.update_status(item)
                self.add_history(
                    inventory_id,
                    "REMOVE",
                    quantity,
                    previous_quantity,
                    new_quantity
                )
                self.save_data()
                print(
                    f"{quantity} {item['unit']} of {item['item_name']} consumed successfully."
                )
                print(f"Remaining quantity: {item['current_quantity']} {item['unit']}")
                return
        print("Inventory item not found.")

    def update_stock(self, inventory_id, new_quantity):
        for item in self.inventory:
            if item["inventory_id"] == inventory_id:
                if new_quantity < 0:
                    print("Quantity cannot be negative.")
                    return
                if new_quantity > item["maximum_capacity"]:
                    print("Cannot update stock. Maximum capacity exceeded.")
                    return
                previous_quantity = item["current_quantity"]
                item["current_quantity"] = new_quantity
                item["last_updated"] = datetime.now(timezone.utc).isoformat()
                self.update_status(item)
                self.add_history(
                    inventory_id,
                    "ADJUSTMENT",
                    new_quantity - previous_quantity,
                    previous_quantity,
                    new_quantity
                )
                self.save_data()
                print(
                    f"{item['item_name']} quantity updated successfully."
                )
                print(
                    f"New quantity: {item['current_quantity']} {item['unit']}"
                )
                return
        print("Inventory item not found.")

    def view_history(self):
        if not self.history:
            print("No inventory history available.")
            return

        for record in self.history:
            print(
                f"Inventory ID: {record['inventory_id']} | "
                f"Action: {record['action']} | "
                f"Quantity: {record['quantity']} | "
                f"Before: {record['previous_quantity']} | "
                f"After: {record['new_quantity']} | "
                f"Time: {record['timestamp']}"
            )

    def get_consumption_history(self, inventory_id):
        consumption_history = []
        for record in self.history:
            if (
                record["inventory_id"] == inventory_id
                and record["action"] == "REMOVE"
            ):
                consumption_history.append(record)
        return consumption_history

    def calculate_average_daily_consumption(self, inventory_id):
        consumption_history = self.get_consumption_history(inventory_id)
        if not consumption_history:
            return 0
        total_consumption = sum(
            record["quantity"]
            for record in consumption_history
        )
        dates = [
            record["timestamp"][:10]
            for record in consumption_history
        ]
        unique_dates = set(dates)
        if len(unique_dates) == 1:
            return total_consumption
        return total_consumption / len(unique_dates)

    def calculate_days_of_stock_remaining(self, inventory_id):
        for item in self.inventory:
            if item["inventory_id"] == inventory_id:
                average_consumption = self.calculate_average_daily_consumption(
                    inventory_id
                )
                if average_consumption <= 0:
                    return None
                return item["current_quantity"] / average_consumption
        return None

    def calculate_predicted_depletion_date(self, inventory_id):
        days_remaining = self.calculate_days_of_stock_remaining(
            inventory_id
        )
        if days_remaining is None:
            return None
        depletion_date = datetime.now(timezone.utc) + timedelta(
            days=days_remaining
        )
        return depletion_date.date().isoformat()

    def update_status(self, item):
        if item["current_quantity"] <= item["minimum_quantity"]:
            item["status"] = "Critical"
        elif item["current_quantity"] <= item["minimum_quantity"] * 1.5:
            item["status"] = "Low"
        else:
            item["status"] = "Normal"

    def check_alerts(self):
        for item in self.inventory:
            self.update_status(item)
            if item["status"] == "Critical":
                print(
                    f"CRITICAL ALERT: {item['item_name']} "
                    f"at {item['station_id']} is critically low."
                )
            elif item["status"] == "Low":
                print(
                    f"LOW STOCK ALERT: {item['item_name']} "
                    f"at {item['station_id']} is running low."
                )