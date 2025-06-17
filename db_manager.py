import sqlite3
import threading
from datetime import datetime

class DBManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path="cloud_kitchen.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = DBManager()
            return cls._instance

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                resource_name TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                available INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS allocations (
                order_id TEXT NOT NULL,
                resource_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                PRIMARY KEY (order_id, resource_name),
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (resource_name) REFERENCES resources(resource_name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                timestamp TEXT NOT NULL,
                event TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def get_resources(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT resource_name, total, available FROM resources")
        rows = cursor.fetchall()
        return {row["resource_name"]: {"total": row["total"], "available": row["available"]} for row in rows}

    def upsert_resource(self, resource_name, total, available):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO resources (resource_name, total, available)
            VALUES (?, ?, ?)
            ON CONFLICT(resource_name) DO UPDATE SET
                total=excluded.total,
                available=excluded.available
        """, (resource_name, total, available))
        self.conn.commit()

    def get_orders(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT order_id, status, priority FROM orders")
        rows = cursor.fetchall()
        return {row["order_id"]: {"status": row["status"], "priority": row["priority"]} for row in rows}

    def upsert_order(self, order_id, status, priority):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO orders (order_id, status, priority)
            VALUES (?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                status=excluded.status,
                priority=excluded.priority
        """, (order_id, status, priority))
        self.conn.commit()

    def delete_order(self, order_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        cursor.execute("DELETE FROM allocations WHERE order_id = ?", (order_id,))
        self.conn.commit()

    def get_allocations(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT order_id, resource_name, quantity FROM allocations")
        rows = cursor.fetchall()
        allocations = {}
        for row in rows:
            allocations.setdefault(row["order_id"], {})[row["resource_name"]] = row["quantity"]
        return allocations

    def upsert_allocation(self, order_id, resource_name, quantity):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO allocations (order_id, resource_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(order_id, resource_name) DO UPDATE SET
                quantity=excluded.quantity
        """, (order_id, resource_name, quantity))
        self.conn.commit()

    def delete_allocations_for_order(self, order_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM allocations WHERE order_id = ?", (order_id,))
        self.conn.commit()

    def log_event(self, event):
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute("INSERT INTO logs (timestamp, event) VALUES (?, ?)", (timestamp, event))
        self.conn.commit()

    def get_logs(self, limit=100):
        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp, event FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [{"timestamp": row["timestamp"], "event": row["event"]} for row in rows]

    def close(self):
        self.conn.close()
