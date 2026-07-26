from models import DroneMove, MoveState, SimulationTurn

ZoneState = tuple[str, int]


class Simulation:
    """Converts planned drone paths into turn-by-turn simulation moves."""

    def __init__(self, drone_paths: list[list[ZoneState]]) -> None:
        self.drone_paths = drone_paths

    def _drone_moves(
        self,
        drone_id: int,
        path: list[ZoneState],
    ) -> dict[int, DroneMove]:
        """Generate turn-by-turn moves for a single drone path."""
        moves: dict[int, DroneMove] = {}

        for (z1, t1), (z2, t2) in zip(path, path[1:]):
            if z1 == z2:
                moves[t2] = DroneMove(
                    drone_id=drone_id,
                    from_zone=z1,
                    to_zone=z1,
                    state=MoveState.WAITING,
                )
                continue

            for t in range(t1 + 1, t2):
                moves[t] = DroneMove(
                    drone_id=drone_id,
                    from_zone=z1,
                    to_zone=z2,
                    state=MoveState.TRANSIT,
                )

            moves[t2] = DroneMove(
                drone_id=drone_id,
                from_zone=z1,
                to_zone=z2,
                state=MoveState.ARRIVED,
            )

        return moves

    def run(self) -> list[SimulationTurn]:
        """Run simulation and return list of turns."""
        per_turn: dict[int, list[DroneMove]] = {}

        for drone_id, path in enumerate(self.drone_paths, start=1):
            for turn, move in self._drone_moves(drone_id, path).items():
                per_turn.setdefault(turn, []).append(move)

        turns: list[SimulationTurn] = []

        for number in sorted(per_turn):
            turns.append(
                SimulationTurn(
                    number=number,
                    moves=per_turn[number],
                )
            )

        return turns
