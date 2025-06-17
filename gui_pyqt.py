"""
PyQt5 GUI for Cloud Kitchen Deadlock Simulator with academic-style features:
- Dashboard, Simulation Panel, RAG visualization, Log Console
- Educational mode, real-time controls, export logs, quiz mode
"""

import sys
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QTextEdit,
                             QInputDialog, QMessageBox, QFileDialog)
from PyQt5.QtCore import QTimer, Qt
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from resource_manager import ResourceManager
from order_manager import OrderManager
from deadlock_detector import DeadlockDetector

class RAGCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(figsize=(5,5))
        super().__init__(self.fig)
        self.setParent(parent)

    def draw_rag(self, resource_manager, order_manager, deadlocks):
        self.ax.clear()
        G = nx.DiGraph()

        # Add nodes for orders and resources
        for order_id in list(order_manager.get_active_orders().keys()) + list(order_manager.get_current_requests().keys()):
            G.add_node(order_id, type='order')
        for res in resource_manager.total_resources.keys():
            G.add_node(res, type='resource')

        # Add edges for allocations (resource -> order)
        allocations = resource_manager.allocated_resources
        for order_id, res_dict in allocations.items():
            for res, qty in res_dict.items():
                if qty > 0:
                    G.add_edge(res, order_id, label=str(qty))

        # Add edges for requests (order -> resource)
        requests = order_manager.get_current_requests()
        for order_id, res_dict in requests.items():
            for res, qty in res_dict.items():
                if qty > 0:
                    G.add_edge(order_id, res, label=str(qty))

        # Color nodes: red for deadlocked orders, green for safe resources/orders
        node_colors = []
        deadlocked_orders = set(o for cycle in deadlocks for o in cycle)
        for node in G.nodes():
            if node in deadlocked_orders:
                node_colors.append('red' if G.nodes[node].get('type') == 'order' else 'orange')
            else:
                node_colors.append('lightgreen' if G.nodes[node].get('type') == 'order' else 'lightblue')

        pos = nx.spring_layout(G)
        nx.draw(G, pos, ax=self.ax, with_labels=True, node_color=node_colors,
                node_size=1500, font_size=10, font_weight='bold', arrowsize=20)
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=self.ax, font_color='blue')
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cloud Kitchen Deadlock Simulator")
        self.resize(1200, 800)

        # Initialize backend
        self.resources = {
            "Oven": 1,
            "Chef": 2,
            "Delivery_Bike": 1,
            "Ingredients": 5
        }
        self.resource_manager = ResourceManager(self.resources)
        self.order_manager = OrderManager(self.resource_manager)
        self.deadlock_detector = DeadlockDetector(self.resource_manager)

        self.order_counter = 1
        self.simulation_running = False

        self.init_ui()
        self.update_status()

        # Timer for simulation loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulation_step)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Left panel: Dashboard and Simulation controls
        left_panel = QVBoxLayout()

        # Resource status tree
        self.resource_tree = QTreeWidget()
        self.resource_tree.setHeaderLabels(["Resource", "Total", "Available"])
        left_panel.addWidget(QLabel("Resources"))
        left_panel.addWidget(self.resource_tree)

        # Orders status tree
        self.orders_tree = QTreeWidget()
        self.orders_tree.setHeaderLabels(["Order ID", "Status", "Resources"])
        left_panel.addWidget(QLabel("Orders"))
        left_panel.addWidget(self.orders_tree)

        # Simulation buttons
        btn_layout = QHBoxLayout()
        self.add_order_btn = QPushButton("Add Order")
        self.add_order_btn.clicked.connect(self.add_order)
        btn_layout.addWidget(self.add_order_btn)

        self.detect_btn = QPushButton("Detect Deadlocks")
        self.detect_btn.clicked.connect(self.detect_deadlocks)
        btn_layout.addWidget(self.detect_btn)

        self.avoid_btn = QPushButton("Check Safe State")
        self.avoid_btn.clicked.connect(self.check_safe_state)
        btn_layout.addWidget(self.avoid_btn)

        self.release_btn = QPushButton("Release Selected Order")
        self.release_btn.clicked.connect(self.release_order)
        btn_layout.addWidget(self.release_btn)

        self.abort_btn = QPushButton("Abort Selected Order")
        self.abort_btn.clicked.connect(self.abort_order)
        btn_layout.addWidget(self.abort_btn)

        left_panel.addLayout(btn_layout)

        # More buttons
        btn_layout2 = QHBoxLayout()
        self.add_resource_btn = QPushButton("Add Virtual Resources")
        self.add_resource_btn.clicked.connect(self.add_virtual_resources)
        btn_layout2.addWidget(self.add_resource_btn)

        self.preempt_btn = QPushButton("Preempt Resources")
        self.preempt_btn.clicked.connect(self.preempt_resources)
        btn_layout2.addWidget(self.preempt_btn)

        left_panel.addLayout(btn_layout2)

        # Simulation control buttons
        sim_ctrl_layout = QHBoxLayout()
        self.play_btn = QPushButton("Play Simulation")
        self.play_btn.clicked.connect(self.play_simulation)
        sim_ctrl_layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause Simulation")
        self.pause_btn.clicked.connect(self.pause_simulation)
        sim_ctrl_layout.addWidget(self.pause_btn)

        self.reset_btn = QPushButton("Reset Simulation")
        self.reset_btn.clicked.connect(self.reset_simulation)
        sim_ctrl_layout.addWidget(self.reset_btn)

        left_panel.addLayout(sim_ctrl_layout)

        # Quiz mode button
        self.quiz_btn = QPushButton("Quiz Mode")
        self.quiz_btn.clicked.connect(self.quiz_mode)
        left_panel.addWidget(self.quiz_btn)

        # Log console
        left_panel.addWidget(QLabel("Event Log"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        left_panel.addWidget(self.log_text)

        main_layout.addLayout(left_panel, 3)

        # Right panel: RAG visualization and explanation
        right_panel = QVBoxLayout()

        self.rag_canvas = RAGCanvas(self)
        right_panel.addWidget(self.rag_canvas)

        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        right_panel.addWidget(QLabel("Step-by-Step Explanation"))
        right_panel.addWidget(self.explanation_text)

        main_layout.addLayout(right_panel, 4)

    def update_status(self):
        # Update resource tree
        self.resource_tree.clear()
        status = self.resource_manager.get_status()
        for res, total in status["total"].items():
            available = status["available"].get(res, 0)
            item = QTreeWidgetItem([res, str(total), str(available)])
            self.resource_tree.addTopLevelItem(item)

        # Update orders tree
        self.orders_tree.clear()
        active_orders = self.order_manager.get_active_orders()
        pending_requests = self.order_manager.get_current_requests()

        deadlocks = self.deadlock_detector.detect(pending_requests)
        deadlocked_orders = set(o for cycle in deadlocks for o in cycle)

        for order_id, resources in active_orders.items():
            res_str = ", ".join(f"{k}:{v}" for k, v in resources.items())
            status_str = "Allocated (Deadlocked)" if order_id in deadlocked_orders else "Allocated"
            item = QTreeWidgetItem([order_id, status_str, res_str])
            if order_id in deadlocked_orders:
                item.setBackground(1, Qt.red)
                item.setBackground(0, Qt.red)
                item.setBackground(2, Qt.red)
            self.orders_tree.addTopLevelItem(item)

        for order_id, resources in pending_requests.items():
            res_str = ", ".join(f"{k}:{v}" for k, v in resources.items())
            status_str = "Pending (Deadlocked)" if order_id in deadlocked_orders else "Pending"
            item = QTreeWidgetItem([order_id, status_str, res_str])
            if order_id in deadlocked_orders:
                item.setBackground(1, Qt.red)
                item.setBackground(0, Qt.red)
                item.setBackground(2, Qt.red)
            self.orders_tree.addTopLevelItem(item)

        self.rag_canvas.draw_rag(self.resource_manager, self.order_manager, deadlocks)
        self.update_explanation(deadlocks)
        self.update_log(f"Status updated. Deadlocks detected: {len(deadlocks)}")

    def update_explanation(self, deadlocks):
        self.explanation_text.clear()
        if deadlocks:
            self.explanation_text.append("Deadlock detected among the following orders:")
            for cycle in deadlocks:
                self.explanation_text.append(" -> ".join(cycle))
            self.explanation_text.append("\nResolution strategies:")
            self.explanation_text.append("- Preempt resources from one or more orders.")
            self.explanation_text.append("- Abort or rollback orders to break the deadlock.")
            self.explanation_text.append("- Use avoidance techniques like Banker's Algorithm to prevent unsafe states.")
        else:
            self.explanation_text.append("No deadlocks detected. System is in a safe state.")

    def update_log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"{timestamp} - {message}")

    def add_order(self):
        resource_request = {}
        for res in self.resource_manager.total_resources.keys():
            qty, ok = QInputDialog.getInt(self, "Resource Request",
                                          f"Enter quantity of {res} for order {self.order_counter}:",
                                          0, 0, self.resource_manager.total_resources[res])
            if not ok:
                return
            if qty > 0:
                resource_request[res] = qty
        if not resource_request:
            QMessageBox.information(self, "Info", "No resources requested.")
            return
        order_id = f"Order{self.order_counter}"
        self.order_manager.create_order(order_id, resource_request)
        self.order_manager.process_orders()
        self.order_counter += 1
        self.update_status()
        self.update_log(f"Order {order_id} added with resources {resource_request}")

    def detect_deadlocks(self):
        requests = self.order_manager.get_current_requests()
        deadlocks = self.deadlock_detector.detect(requests)
        if deadlocks:
            msg = "Deadlock detected among orders:\n"
            for cycle in deadlocks:
                msg += ", ".join(cycle) + "\n"
            QMessageBox.warning(self, "Deadlock Detected", msg)
            self.update_log("Deadlock detected: " + msg.replace('\n', ' '))
        else:
            QMessageBox.information(self, "No Deadlock", "No deadlocks detected.")
            self.update_log("No deadlocks detected.")
        self.update_status()

    def check_safe_state(self):
        max_demand = {}
        allocation = self.resource_manager.allocated_resources
        available = self.resource_manager.available_resources
        for order_id in set(list(allocation.keys()) + list(self.order_manager.get_current_requests().keys())):
            max_demand[order_id] = {}
            alloc = allocation.get(order_id, {})
            req = self.order_manager.get_current_requests().get(order_id, {})
            for res in set(list(alloc.keys()) + list(req.keys())):
                max_demand[order_id][res] = max(alloc.get(res, 0), req.get(res, 0))
        safe = self.deadlock_detector.bankers_algorithm(max_demand, allocation, available)
        if safe:
            QMessageBox.information(self, "Safe State", "The system is in a safe state (no deadlock risk).")
            self.update_log("System is in a safe state according to Banker's Algorithm.")
        else:
            QMessageBox.warning(self, "Unsafe State", "The system is in an unsafe state (deadlock risk present).")
            self.update_log("System is in an unsafe state according to Banker's Algorithm.")
        self.update_status()

    def release_order(self):
        selected_items = self.orders_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "No order selected.")
            return
        for item in selected_items:
            order_id = item.text(0)
            self.order_manager.release_order(order_id)
            self.update_log(f"Order {order_id} released.")
        self.update_status()

    def abort_order(self):
        selected_items = self.orders_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "No order selected to abort.")
            return
        for item in selected_items:
            order_id = item.text(0)
            self.order_manager.release_order(order_id)
            self.update_log(f"Order {order_id} aborted.")
        self.update_status()

    def add_virtual_resources(self):
        additions = {}
        for res in self.resource_manager.total_resources.keys():
            qty, ok = QInputDialog.getInt(self, "Add Virtual Resources",
                                          f"Enter quantity of {res} to add:", 0, 0)
            if not ok:
                return
            if qty > 0:
                additions[res] = qty
        if not additions:
            QMessageBox.information(self, "Info", "No resources added.")
            return
        self.resource_manager.add_virtual_resources(additions)
        self.update_log(f"Virtual resources added: {additions}")
        self.update_status()

    def preempt_resources(self):
        selected_items = self.orders_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "No order selected to preempt resources from.")
            return
        for item in selected_items:
            order_id = item.text(0)
            self.resource_manager.preempt_resources(order_id)
            self.order_manager.release_order(order_id)
            self.update_log(f"Resources preempted from order {order_id}. Order aborted.")
        self.update_status()

    def play_simulation(self):
        if self.simulation_running:
            self.update_log("Simulation already running.")
            return
        self.simulation_running = True
        self.timer.start(3000)
        self.update_log("Simulation started.")

    def pause_simulation(self):
        if not self.simulation_running:
            self.update_log("Simulation not running.")
            return
        if self.timer.isActive():
            self.timer.stop()
            self.update_log("Simulation paused.")
        else:
            self.timer.start(3000)
            self.update_log("Simulation resumed.")

    def reset_simulation(self):
        self.simulation_running = False
        self.timer.stop()
        self.order_manager.orders.clear()
        self.order_manager.pending_requests.clear()
        self.order_manager.order_priorities.clear()
        self.resource_manager.available_resources = self.resource_manager.total_resources.copy()
        self.resource_manager.allocated_resources.clear()
        self.order_counter = 1
        self.update_log("Simulation reset.")
        self.update_status()

    def simulation_step(self):
        # Add random order with random resource requests
        resource_request = {}
        for res in self.resource_manager.total_resources.keys():
            max_qty = self.resource_manager.total_resources[res]
            qty = 0
            if max_qty > 0:
                qty = max(0, int(max_qty * 0.5))
            if qty > 0:
                resource_request[res] = qty
        if resource_request:
            order_id = f"Order{self.order_counter}"
            self.order_manager.create_order(order_id, resource_request)
            self.order_manager.process_orders()
            self.update_log(f"Simulation: Added {order_id} with resources {resource_request}")
            self.order_counter += 1
            self.update_status()

    def quiz_mode(self):
        questions = [
            {
                "question": "What is a deadlock in resource allocation?",
                "options": ["A state where all resources are free", "A state where processes wait indefinitely", "A state where resources are abundant"],
                "answer": 1
            },
            {
                "question": "Which algorithm is used for deadlock avoidance?",
                "options": ["Banker's Algorithm", "Dijkstra's Algorithm", "Bellman-Ford Algorithm"],
                "answer": 0
            },
            {
                "question": "What is a common method to resolve deadlocks?",
                "options": ["Process termination", "Increasing resources", "Ignoring the problem"],
                "answer": 0
            }
        ]
        score = 0
        for q in questions:
            answer, ok = QInputDialog.getInt(self, "Quiz",
                                            f"{q['question']}\nOptions:\n" + "\n".join(f"{i}. {opt}" for i, opt in enumerate(q['options'])),
                                            0, 0, len(q['options'])-1)
            if ok and answer == q['answer']:
                score += 1
        QMessageBox.information(self, "Quiz Result", f"You scored {score} out of {len(questions)}")
        self.update_log(f"Quiz completed with score {score}/{len(questions)}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
