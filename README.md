*This project has been created as part of the 42 curriculum by wabbad.*

# Fly-In: Autonomous Drone Routing & Visualization System

## Description

**Fly-In** is a high-performance, object-oriented drone routing simulation engine written in Python 3.12. The system coordinates multiple autonomous drones through a network of connected hubs/zones, minimizing total simulation turns while strictly observing node capacities (`max_drones`), edge capacities (`max_link_capacity`), and variable movement turn costs across diverse zone types (`normal`, `restricted`, `priority`, `blocked`).

The project includes an interactive graphical visualizer (Pygame GUI & Web Canvas) and a colored terminal renderer to analyze routing performance and turn-by-turn drone dynamics.

---

## Visual Representation Features

The visual representation engine provides full real-time visual feedback of drone movements and graph states:

1. **Pygame Graphical Interface (`--vis`)**:
   - **Interactive Simulation Controls**: Play/Pause (`Space`), Step Forward (`Right Arrow`), Step Backward (`Left Arrow`), Speed Adjustment (`Up/Down Arrows` from 0.5x to 5.0x), and Reset (`R`).
   - **Dynamic Network Graph**: Automatic coordinate scaling and layout, displaying zone names, zone types, color metadata, and max capacity badges (`max_drones`).
   - **Connection Capacity & Transit**: Displays link capacities (`max_link_capacity`) and smooth interpolation of drones moving between nodes, including 2-turn transit states through restricted zones.
   - **Telemetry Panel**: Live display of turn numbers, total turns, drone states, and active execution mode.

2. **Interactive Web Dashboard (`--web`)**:
   - Generates an HTML5 canvas visualizer (`visualizer.html`) with an interactive turn slider, play/pause controls, and zone state displays for viewing in any web browser.

3. **ANSI Colored Terminal Mode (`--cli`)**:
   - Outputs step-by-step drone movements with color codes (`[Turn N] D1-zoneA D2-zoneB`) for command-line evaluations.

---

## Instructions

### Installation
Install project dependencies (`pygame`, `flake8`, `mypy`):
```bash
make install
```

### Execution
Run simulation output on a map file:
```bash
python3 main.py maps/easy/01_linear_path.txt
```
Or via Makefile:
```bash
make run MAP=maps/easy/01_linear_path.txt
```

### Visualizer Usage
Launch the **Pygame Graphical Visualizer**:
```bash
python3 main.py --vis maps/easy/01_linear_path.txt
# OR
python3 visualizer.py maps/easy/01_linear_path.txt
```

Launch the **Web Browser Visualizer**:
```bash
python3 main.py --web maps/easy/01_linear_path.txt
# OR
python3 visualizer.py --web maps/easy/01_linear_path.txt
```

Run **ANSI Colored Terminal Output**:
```bash
python3 main.py --cli maps/easy/01_linear_path.txt
```

### Linting & Static Typing
Execute strict linting and type checking:
```bash
make lint
make lint-strict
```

### Cleanup
Clean caches and temporary files:
```bash
make clean
```

---

## Algorithm Strategy & Choices

1. **Time-Expanded Reservation Graph**:
   - Routes drones by computing collision-free time-space paths from the start zone to the end zone.
   - Respects zone arrival capacities (`max_drones`), connection traversal capacities (`max_link_capacity`), and 2-turn movement delays for `restricted` zones.
2. **Prioritized Multi-Path Distribution**:
   - Distributes drones across available disjoint and overlapping routes to maximize overall throughput and avoid bottleneck deadlocks.

---

## Resources & AI Usage

### References
- *Python 3 Typing Documentation*: [docs.python.org/3/library/typing.html](https://docs.python.org/3/library/typing.html)
- *Pygame Community Documentation*: [pygame.org/docs](https://www.pygame.org/docs/)
- *Graph Theory & Time-Expanded Networks*: Network Routing Algorithms Primer.

### AI Usage Disclosure
In accordance with Chapter II instructions, AI tools were used for:
- Writing Pygame coordinate scaling logic and canvas HTML structure.
- Refactoring docstrings and PEP 257 standard compliance.
- All code logic was critically reviewed, tested against mypy strict type checks, and verified via simulation runs.
