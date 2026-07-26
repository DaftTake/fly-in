from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ZoneType(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class MoveState(str, Enum):
    WAITING = "waiting"
    TRANSIT = "transit"
    ARRIVED = "arrived"


@dataclass
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False


@dataclass
class Connection:
    zone_a: str
    zone_b: str
    max_link_capacity: int = 1


@dataclass
class SimConfig:
    nb_drones: int
    zones: dict[str, Zone]
    connections: list[Connection]


@dataclass(frozen=True)
class DroneMove:
    drone_id: int
    from_zone: str
    to_zone: str
    state: MoveState


@dataclass
class SimulationTurn:
    number: int
    moves: list[DroneMove]
