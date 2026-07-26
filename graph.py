from models import Connection, SimConfig, Zone, ZoneType


class Graph:
    """Graph representation of zones and connections."""

    def __init__(self, config: SimConfig) -> None:
        self.zones: dict[str, Zone] = config.zones
        self.adjacency: dict[str, list[tuple[str, Connection]]] = {}
        self._build_graph(config.connections)

    def _build_graph(self, connections: list[Connection]) -> None:
        """Build adjacency list from connections."""
        for zone_name in self.zones:
            self.adjacency[zone_name] = []

        for conn in connections:
            self.adjacency[conn.zone_a].append((conn.zone_b, conn))
            self.adjacency[conn.zone_b].append((conn.zone_a, conn))

    def get_neighbor(self, zone_name: str) -> list[tuple[str, Connection]]:
        """Get neighbors of a zone."""
        return self.adjacency.get(zone_name, [])

    def get_movement_cost(self, destination_zone: str) -> int:
        """Get movement cost for entering a zone."""
        zone = self.zones[destination_zone]
        if zone.zone_type == ZoneType.RESTRICTED:
            return 2
        return 1

    def is_traversable(self, zone_name: str) -> bool:
        """Check if a zone can be entered."""
        return self.zones[zone_name].zone_type != ZoneType.BLOCKED

    @property
    def node_count(self) -> int:
        """Number of zones in the graph."""
        return len(self.zones)
