
*This project has been created as part of the 42 curriculum by wabbad.*

## Description

**Fly-In** is an autonomous drone routing simulation engine written in Python 3.12. The system coordinates multiple drones through a network of connected hubs, minimizing total simulation turns while observing node capacities (`max_drones`), connection capacities (`max_link_capacity`), and zone movement costs (`normal`, `restricted`, `priority`, `blocked`).

---

## Instructions

### Setup
Install project dependencies:
```bash
make install
```

### Execution
Run simulation output for a map file:
```bash
python3 main.py <path_to_map_file>
```

Launch the Pygame graphical visualizer:
```bash
python3 main.py --vis <path_to_map_file>
```

### Linting & Code Quality
Run static type checking and linter:
```bash
make lint
```

---

## Algorithm Explanation

The pathfinding system uses **Time-Expanded Dijkstra Search**:
- **Time-Expanded States**: Drones are routed through states defined as `(zone_name, turn)`.
- **Shared Reservations**: Each planned path commits reservations to `zone_reservations` and `edge_reservations` tables. Subsequent drones check these tables to avoid collisions and automatically choose waiting or parallel spatial detours.
- **Priority & Costs**: Handles 1-turn normal/priority steps, 2-turn restricted transit delays, and blocked zones.

---

## Visual Representation Features

The Pygame graphical interface (`--vis`) provides real-time visualization:
- **Interactive Controls**: Play/Pause (`Space`), Step Forward (`Right`), Step Backward (`Left`), Speed Control (`Up`/`Down` arrows).
- **Dynamic Topology**: Renders zones, connection capacities, colors, and live drone markers with smooth interpolation.

---

## Example Input and Expected Output

### Input Map File:
```text
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: waypoint1 1 0 [color=blue]
hub: waypoint2 2 0 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-waypoint1
connection: waypoint1-waypoint2
connection: waypoint2-goal
```

### Command:
```bash
python3 main.py <map_file>
```

### Expected Output:
```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```
