from typing import Optional

from graph import Graph
from models import Connection

ZoneState = tuple[str, int]
ZoneReservations = dict[ZoneState, int]
EdgeReservations = dict[tuple[frozenset[str], int], int]


class PathFinder:
    """Finds capacity-respecting paths through a graph for drones."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def single_path_finder(
        self,
        start_zone: str,
        end_zone: str,
        zone_reservations: ZoneReservations,
        edge_reservations: EdgeReservations,
        max_turn: Optional[int] = None,
    ) -> Optional[list[ZoneState]]:
        """Find cheapest path for a single drone respecting capacity."""
        start_state: ZoneState = (start_zone, 0)
        frontier: set[ZoneState] = {start_state}
        dist: dict[ZoneState, float] = {start_state: 0}
        finalized: set[ZoneState] = set()
        parent: dict[ZoneState, Optional[ZoneState]] = {start_state: None}

        while frontier:
            curr_state = min(frontier, key=lambda s: dist.get(s, float("inf")))
            frontier.remove(curr_state)
            finalized.add(curr_state)

            zone, turn = curr_state

            if zone == end_zone:
                return self._construct_the_path(
                    parent, start_state, curr_state)

            for neighbor_name, conn in self.graph.get_neighbor(zone):
                if not self.graph.is_traversable(neighbor_name):
                    continue

                cost = self.graph.get_movement_cost(neighbor_name)
                arrival_turn = turn + cost
                if max_turn is not None and arrival_turn > max_turn:
                    continue
                neighbor_state: ZoneState = (neighbor_name, arrival_turn)

                if neighbor_state in finalized:
                    continue
                if not self._zone_has_room(neighbor_state, zone_reservations):
                    continue
                if not self._edge_has_room(
                    zone, neighbor_name, turn, cost, conn, edge_reservations
                ):
                    continue

                tentative = dist[curr_state] + cost

                if tentative < dist.get(neighbor_state, float("inf")):
                    dist[neighbor_state] = tentative
                    parent[neighbor_state] = curr_state
                    frontier.add(neighbor_state)

            wait_state: ZoneState = (zone, turn + 1)
            if max_turn is not None and (turn + 1) > max_turn:
                continue
            if self._zone_has_room(wait_state, zone_reservations):
                wait_tentative = dist[curr_state] + 1
                if wait_tentative < dist.get(wait_state, float("inf")):
                    dist[wait_state] = wait_tentative
                    parent[wait_state] = curr_state
                    frontier.add(wait_state)

        return None

    def _zone_has_room(
        self, state: ZoneState, zone_reservations: ZoneReservations
    ) -> bool:
        """Check if zone has capacity at given state."""
        zone_name, _turn = state
        occupied = zone_reservations.get(state, 0)
        return occupied < self.graph.zones[zone_name].max_drones

    def _transit_turns(self, depart_turn: int, cost: int) -> range:
        """Get turn range occupied by transit."""
        return range(depart_turn, depart_turn + cost)

    def _edge_has_room(
        self,
        zone_a: str,
        zone_b: str,
        depart_turn: int,
        cost: int,
        conn: Connection,
        edge_reservations: EdgeReservations,
    ) -> bool:
        """Check if connection has capacity during transit."""
        edge_key_base = frozenset({zone_a, zone_b})
        for t in self._transit_turns(depart_turn, cost):
            used = edge_reservations.get((edge_key_base, t), 0)
            if used >= conn.max_link_capacity:
                return False
        return True

    def _construct_the_path(
        self,
        parent: dict[ZoneState, Optional[ZoneState]],
        start: ZoneState,
        end: ZoneState,
    ) -> list[ZoneState]:
        """Reconstruct path from parent pointers."""
        path: list[ZoneState] = []
        current: Optional[ZoneState] = end

        while current is not None:
            path.append(current)
            current = parent[current]

        path.reverse()
        assert path[0] == start
        return path

    def plan_all_drones(
        self, start_zone: str, end_zone: str, nb_drones: int
    ) -> list[list[ZoneState]]:
        """Plan paths for all drones."""
        zone_reservations: ZoneReservations = {}
        edge_reservations: EdgeReservations = {}
        all_paths: list[list[ZoneState]] = []
        max_turn = self.graph.node_count * nb_drones * 2
        for drone_index in range(nb_drones):
            path = self.single_path_finder(
                start_zone, end_zone, zone_reservations, edge_reservations,
                max_turn,
            )
            if path is None:
                raise ValueError(f"Drone {drone_index} has no feasible path")

            all_paths.append(path)

            for zone_name, t in path:
                zone_key = (zone_name, t)
                zone_reservations[zone_key] = zone_reservations.get(
                    zone_key, 0) + 1

            for (z1, t1), (z2, t2) in zip(path, path[1:]):
                if z1 != z2:
                    cost = t2 - t1
                    edge_key_base = frozenset({z1, z2})
                    for t in range(t1, t1 + cost):
                        edge_key = (edge_key_base, t)
                        edge_reservations[edge_key] = edge_reservations.get(
                            edge_key, 0) + 1

        return all_paths
