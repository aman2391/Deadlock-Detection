"""
deadlock_detector.py

Module to implement deadlock detection algorithms.
"""

class DeadlockDetector:
    def __init__(self, resource_manager):
        """
        Initialize with a reference to the ResourceManager.
        """
        self.rm = resource_manager

    def build_wait_for_graph(self, requests):
        """
        Build the Wait-for Graph (WFG) from current allocations and requests.
        requests: dict of order_id -> requested resources (dict)
        Returns: dict of order_id -> set of order_ids it is waiting for
        """
        wfg = {}
        allocations = self.rm.allocated_resources

        # Include all orders holding resources and requesting resources
        all_orders = set(allocations.keys()) | set(requests.keys())

        for order_id in all_orders:
            wfg[order_id] = set()

        for order_id, req in requests.items():
            for res, qty in req.items():
                for holder_id, alloc in allocations.items():
                    if holder_id != order_id and alloc.get(res, 0) > 0:
                        # If requested resource is held by another order, add edge
                        wfg[order_id].add(holder_id)
        return wfg

    def detect_deadlocks(self, wfg):
        """
        Detect cycles in the Wait-for Graph.
        Returns list of sets, each set is a cycle (deadlock group).
        """
        visited = set()
        stack = set()
        deadlocks = []

        def dfs(node, path):
            visited.add(node)
            stack.add(node)
            path.append(node)
            for neighbor in wfg.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in stack:
                    # Cycle detected
                    cycle_start = path.index(neighbor)
                    deadlocks.append(set(path[cycle_start:]))
                    return True
            stack.remove(node)
            path.pop()
            return False

        for node in wfg:
            if node not in visited:
                dfs(node, [])

        return deadlocks

    def detect(self, requests):
        """
        Detect deadlocks given current requests.
        Returns list of deadlock cycles.
        """
        wfg = self.build_wait_for_graph(requests)
        deadlocks = self.detect_deadlocks(wfg)
        return deadlocks

    def bankers_algorithm(self, max_demand, allocation, available):
        """
        Implement Banker's Algorithm to check for safe state.
        max_demand: dict of order_id -> dict of resource_name -> max demand
        allocation: dict of order_id -> dict of resource_name -> allocated
        available: dict of resource_name -> available quantity
        Returns True if system is in safe state, False otherwise.
        """
        work = available.copy()
        finish = {order: False for order in max_demand}
        while True:
            progress = False
            for order, need in max_demand.items():
                if not finish[order]:
                    # Calculate need = max_demand - allocation
                    need_res = {res: need.get(res, 0) - allocation.get(order, {}).get(res, 0) for res in need}
                    if all(need_res[res] <= work.get(res, 0) for res in need_res):
                        for res in allocation.get(order, {}):
                            work[res] = work.get(res, 0) + allocation[order].get(res, 0)
                        finish[order] = True
                        progress = True
            if not progress:
                break
        return all(finish.values())
