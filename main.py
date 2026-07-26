
import sys
from graph import Graph
from parsers import ParseError, Parser
from pathfinder import PathFinder
from renderer import TerminalRenderer
from simulation import Simulation
from visualizer import Visualizer


def main() -> None:
    """Run simulation for specified map."""
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <map_file> [--vis]", file=sys.stderr)
        sys.exit(1)

    vis_mode = "--vis" in sys.argv or "-v" in sys.argv
    positional = [a for a in sys.argv[1:] if a not in ("--vis", "-v")]

    if not positional:
        print("Error: No map file specified.", file=sys.stderr)
        sys.exit(1)

    filepath = positional[0]

    try:
        config = Parser(filepath).parse()
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    graph = Graph(config)
    start = next(z for z in config.zones.values() if z.is_start).name
    end = next(z for z in config.zones.values() if z.is_end).name

    pathfinder = PathFinder(graph)
    try:
        drone_paths = pathfinder.plan_all_drones(
            start,
            end,
            config.nb_drones,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    simulation = Simulation(drone_paths)
    turns = simulation.run()

    if vis_mode:
        Visualizer(config, turns).run()
    else:
        renderer = TerminalRenderer()
        for line in renderer.render(turns):
            print(line)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
