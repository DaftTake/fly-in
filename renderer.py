
from typing import List
from models import MoveState, SimulationTurn


class TerminalRenderer:
    """Renders simulation turns to plain text."""

    def render(self, turns: List[SimulationTurn]) -> List[str]:
        """Render simulation turns into formatted string lines."""
        lines: List[str] = []

        for turn in turns:
            entries: List[str] = []
            for move in turn.moves:
                if move.state == MoveState.WAITING:
                    continue

                if move.state == MoveState.TRANSIT:
                    entries.append(
                        f"D{move.drone_id}-{move.from_zone}-{move.to_zone}"
                    )
                else:
                    entries.append(
                        f"D{move.drone_id}-{move.to_zone}"
                    )

            if entries:
                lines.append(" ".join(entries))

        return lines
