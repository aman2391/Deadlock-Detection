"""
resource_manager.py

Module to manage kitchen resources and allocation.
"""

from db_manager import DBManager

class ResourceManager:
    def __init__(self, resources=None):
        """
        Initialize the resource manager with available resources.
        If resources is None, load from database.
        resources: dict of resource_name -> quantity
        """
        self.db = DBManager.get_instance()
        if resources is None:
            # Load resources from DB
            db_resources = self.db.get_resources()
            self.total_resources = {res: db_resources[res]["total"] for res in db_resources}
            self.available_resources = {res: db_resources[res]["available"] for res in db_resources}
        else:
            self.total_resources = resources.copy()
            self.available_resources = resources.copy()
            # Save initial resources to DB
            for res, qty in resources.items():
                self.db.upsert_resource(res, qty, qty)
        self.allocated_resources = {}  # order_id -> {resource_name: quantity}

    def request_resources(self, order_id, request):
        """
        Request resources for an order.
        request: dict of resource_name -> quantity
        Returns True if resources allocated, False otherwise.
        """
        if self._can_allocate(request):
            self._allocate(order_id, request)
            return True
        return False

    def release_resources(self, order_id):
        """
        Release all resources held by an order.
        """
        if order_id in self.allocated_resources:
            for res, qty in self.allocated_resources[order_id].items():
                self.available_resources[res] += qty
            del self.allocated_resources[order_id]
            # Update DB allocations and resources
            self.db.delete_allocations_for_order(order_id)
            for res in self.total_resources:
                self.db.upsert_resource(res, self.total_resources[res], self.available_resources[res])

    def _can_allocate(self, request):
        """
        Check if requested resources can be allocated.
        """
        for res, qty in request.items():
            if self.available_resources.get(res, 0) < qty:
                return False
        return True

    def _allocate(self, order_id, request):
        """
        Allocate resources to an order.
        """
        for res, qty in request.items():
            self.available_resources[res] -= qty
        self.allocated_resources[order_id] = request.copy()
        # Update DB allocations and resources
        for res, qty in request.items():
            self.db.upsert_allocation(order_id, res, qty)
        for res in self.total_resources:
            self.db.upsert_resource(res, self.total_resources[res], self.available_resources[res])

    def add_virtual_resources(self, additions):
        """
        Add virtual resources to the available and total resources.
        additions: dict of resource_name -> quantity
        """
        for res, qty in additions.items():
            self.total_resources[res] = self.total_resources.get(res, 0) + qty
            self.available_resources[res] = self.available_resources.get(res, 0) + qty
            self.db.upsert_resource(res, self.total_resources[res], self.available_resources[res])

    def preempt_resources(self, order_id):
        """
        Preempt (forcefully release) resources held by an order.
        """
        if order_id in self.allocated_resources:
            for res, qty in self.allocated_resources[order_id].items():
                self.available_resources[res] += qty
            del self.allocated_resources[order_id]
            self.db.delete_allocations_for_order(order_id)
            for res in self.total_resources:
                self.db.upsert_resource(res, self.total_resources[res], self.available_resources[res])

    def get_status(self):
        """
        Return current status of resources.
        """
        return {
            "total": self.total_resources,
            "available": self.available_resources,
            "allocated": self.allocated_resources
        }
