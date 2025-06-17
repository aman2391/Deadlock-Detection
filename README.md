# Virtual Kitchen Deadlock Detection System

## Overview
This project simulates a virtual kitchen environment where multiple food orders compete for shared resources such as chefs, ovens, stoves, utensils, and ingredients. The system detects and resolves deadlocks that may occur due to circular waiting for resources.

## Features
- Resource management and allocation
- Dynamic order simulation with resource requests
- Deadlock detection using Wait-for Graph algorithm
- Interactive Tkinter GUI for order simulation, resource tracking, and deadlock visualization
- Options to release orders to resolve deadlocks
- Sample kitchen resources and orders for demonstration

## Architecture
- `resource_manager.py`: Manages kitchen resources and allocation to orders.
- `order_manager.py`: Simulates orders and their resource requests.
- `deadlock_detector.py`: Implements deadlock detection algorithms (Wait-for Graph).
- `gui.py`: Tkinter-based GUI for interactive simulation and visualization.
- `main.py`: Entry point to launch the GUI application.

## How to Run
1. Ensure Python 3.x is installed.
2. Run the application:
   ```
   python main.py
   ```
3. Use the GUI to add orders by specifying resource requests.
4. Detect deadlocks using the "Detect Deadlocks" button.
5. Release orders to free resources and resolve deadlocks.

## Deadlock Detection Algorithm
The system uses the Wait-for Graph (WFG) algorithm:
- Builds a graph where nodes are orders.
- Edges represent waiting relationships (order A waits for resources held by order B).
- Detects cycles in the graph indicating deadlocks.

## Future Extensions
- Implement Banker's Algorithm for deadlock avoidance.
- Add resource preemption and order cancellation options.
- Enhance GUI with visualization of the Wait-for Graph.
- Add logging of deadlock scenarios.

## License
MIT License
