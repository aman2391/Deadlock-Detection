"""
order_manager.py

Module to simulate orders and resource requests dynamically.
"""

import random

from db_manager import DBManager

class OrderManager:
    def __init__(self, resource_manager):
        """
        Initialize with a reference to the ResourceManager.
        Load orders and allocations from database.
        """
        self.rm = resource_manager
        self.db = DBManager.get_instance()
        self.orders = {}  # order_id -> current allocated resources
        self.pending_requests = {}  # order_id -> requested resources
        self.order_priorities = {}  # order_id -> priority (lower number = higher priority)
        self.holding_orders = set()  # orders currently holding resources but waiting

        # Load orders from DB
        db_orders = self.db.get_orders()
        db_allocations = self.db.get_allocations()

        for order_id, data in db_orders.items():
            status = data["status"]
            priority = data["priority"]
            self.order_priorities[order_id] = priority
            if status == "allocated":
                alloc = db_allocations.get(order_id, {})
                self.orders[order_id] = alloc
            elif status == "pending":
                # For pending, load requested resources from allocations or empty
                self.pending_requests[order_id] = db_allocations.get(order_id, {})

    def create_order(self, order_id, resource_request, priority=5):
        """
        Create a new order with a resource request and priority.
        """
        self.pending_requests[order_id] = resource_request
        self.order_priorities[order_id] = priority
        self.db.upsert_order(order_id, "pending", priority)

    def process_orders(self):
        """
        Try to allocate resources for pending requests based on priority.
        Simulate holding resources partially to create deadlock.
        """
        to_remove = []
        # Sort pending requests by priority (lower number first)
        sorted_requests = sorted(self.pending_requests.items(), key=lambda x: self.order_priorities.get(x[0], 5))
        for order_id, request in sorted_requests:
            # Simulate allocation: allocate all requested resources but do not release until explicitly done
            if self.rm._can_allocate(request):
                self.rm._allocate(order_id, request)
                self.orders[order_id] = request
                self.db.upsert_order(order_id, "allocated", self.order_priorities[order_id])
                to_remove.append(order_id)
            else:
                # Cannot allocate resources now, keep pending
                pass
        for order_id in to_remove:
            if order_id in self.pending_requests:
                del self.pending_requests[order_id]

    def release_order(self, order_id):
        """
        Release resources held by an order and remove it.
        """
        self.rm.release_resources(order_id)
        if order_id in self.orders:
            del self.orders[order_id]
        if order_id in self.pending_requests:
            del self.pending_requests[order_id]
        if order_id in self.order_priorities:
            del self.order_priorities[order_id]
        self.db.delete_order(order_id)

    def reschedule_order(self, order_id, new_priority):
        """
        Change the priority of an order.
        """
        if order_id in self.order_priorities:
            self.order_priorities[order_id] = new_priority
            status = "allocated" if order_id in self.orders else "pending"
            self.db.upsert_order(order_id, status, new_priority)

    def cancel_order(self, order_id):
        """
        Cancel an order by releasing resources and removing it.
        """
        self.release_order(order_id)

    def get_current_requests(self):
        """
        Return current pending requests.
        """
        return self.pending_requests.copy()

    def get_active_orders(self):
        """
        Return currently allocated orders.
        """
        return self.orders.copy()
