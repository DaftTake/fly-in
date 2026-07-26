import re
from typing import Optional

from models import Connection, SimConfig, Zone, ZoneType

VALID_COLORS = {
    "red",
    "orange",
    "yellow",
    "gold",
    "green",
    "lime",
    "blue",
    "cyan",
    "purple",
    "magenta",
    "brown",
    "black",
    "maroon",
    "darkred",
    "violet",
    "crimson",
    "rainbow",
}

VALID_ZONE_METADATA_KEYS = {"zone", "color", "max_drones"}
VALID_CONNECTION_METADATA_KEYS = {"max_link_capacity"}


class ParseError(Exception):
    def __init__(self, line_num: int, message: str):
        super().__init__(f"Line {line_num}: {message}")
        self.line_num = line_num


class ParseWarning:
    """Collects non-fatal warnings raised during parsing."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def add(self, line_num: int, message: str) -> None:
        self.messages.append(f"Line {line_num}: {message}")

    def __bool__(self) -> bool:
        return bool(self.messages)


class Parser:
    """Parses a map text file into a SimConfig."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.nb_drones: Optional[int] = None
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.warnings = ParseWarning()
        self._seen_connections: set[frozenset[str]] = set()
        self._seen_coords: dict[tuple[int, int], str] = {}
        self._has_start = False
        self._has_end = False

    def parse(self) -> SimConfig:
        for line_num, raw_line in enumerate(self._read_lines(), start=1):
            self._parse_line(raw_line, line_num)
        self._validate_final_state()

        assert self.nb_drones is not None
        return SimConfig(
            nb_drones=self.nb_drones,
            zones=self.zones,
            connections=self.connections,
        )

    def _read_lines(self) -> list[str]:
        try:
            with open(self.filepath) as f:
                return f.readlines()
        except OSError as e:
            raise ParseError(0, f"Could not open file '{self.filepath}': {e}")

    def _parse_line(self, raw_line: str, line_num: int) -> None:
        line = raw_line.strip()
        if not line:
            return
        if line.startswith("#"):
            return

        match = re.search(r'\s#', line)
        if match:
            line = line[:match.start()].strip()

        if line.startswith("nb_drones:"):
            self._parse_nb_drones(line, line_num)
        elif line.startswith("start_hub:"):
            self._parse_hub_line(
                line,
                line_num,
                prefix="start_hub:",
                is_start=True,
                is_end=False,
            )
        elif line.startswith("end_hub:"):
            self._parse_hub_line(
                line, line_num, prefix="end_hub:", is_start=False, is_end=True
            )
        elif line.startswith("hub:"):
            self._parse_hub_line(
                line, line_num, prefix="hub:", is_start=False, is_end=False
            )
        elif line.startswith("connection:"):
            self._parse_connection_line(line, line_num)
        else:
            raise ParseError(line_num, f"Unrecognized line: '{line}'")

    def _parse_nb_drones(self, line: str, line_num: int) -> None:
        if self.nb_drones is not None:
            raise ParseError(line_num, "Duplicate 'nb_drones' definition")
        raw = line[len("nb_drones:"):].strip()
        self.nb_drones = self._parse_positive_int(raw, line_num, "nb_drones")

    def _parse_hub_line(
        self,
        line: str,
        line_num: int,
        prefix: str,
        is_start: bool,
        is_end: bool,
    ) -> None:
        if self.nb_drones is None:
            raise ParseError(line_num, "'nb_drones' must be defined first")
        if is_start and self._has_start:
            raise ParseError(line_num, "Duplicate 'start_hub' definition")
        if is_end and self._has_end:
            raise ParseError(line_num, "Duplicate 'end_hub' definition")

        remainder = line[len(prefix):]
        mandatory, metadata = self._split_mandatory_and_metadata(
            remainder, line_num, valid_keys=VALID_ZONE_METADATA_KEYS
        )

        parts = mandatory.split()
        if len(parts) != 3:
            raise ParseError(
                line_num,
                f"Expected 'name x y', got {len(parts)} token(s): {mandatory}",
            )
        name, raw_x, raw_y = parts

        if "-" in name:
            raise ParseError(
                line_num, f"Zone name '{name}' contains illegal character '-'"
            )
        if " " in name:
            raise ParseError(
                line_num, f"Zone name {name} contains illegal space character"
            )

        if name in self.zones:
            raise ParseError(line_num, f"Duplicate zone name '{name}'")

        x = self._parse_int(raw_x, line_num, "x-coordinate")
        y = self._parse_int(raw_y, line_num, "y-coordinate")

        coord = (x, y)
        if coord in self._seen_coords:
            other = self._seen_coords[coord]
            raise ParseError(
                line_num,
                f"Zone {name} has the same coords ({x}, {y}) as zone {other}",
            )
        self._seen_coords[coord] = name

        raw_type = metadata.get("zone", "normal")
        try:
            zone_type = ZoneType(raw_type)
        except ValueError:
            valid = [t.value for t in ZoneType]
            raise ParseError(
                line_num,
                f"Invalid zone type '{raw_type}', must be one of: {valid}",
            )

        max_drones = self._resolve_max_drones(
            metadata, line_num, name, is_start, is_end
        )

        color: Optional[str] = metadata.get("color")
        if color is not None and color not in VALID_COLORS:
            raise ParseError(
                line_num,
                f"Invalid color {color}, must be one of: {(VALID_COLORS)}",
            )

        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )
        self.zones[name] = zone
        if is_start:
            self._has_start = True
        if is_end:
            self._has_end = True

    def _resolve_max_drones(
        self,
        metadata: dict[str, str],
        line_num: int,
        zone_name: str,
        is_start: bool,
        is_end: bool,
    ) -> int:
        assert self.nb_drones is not None

        raw_capacity = metadata.get("max_drones")

        if not (is_start or is_end):
            if raw_capacity is None:
                return 1
            return self._parse_positive_int(
                raw_capacity, line_num, "max_drones"
            )

        kind = "start_hub" if is_start else "end_hub"

        if raw_capacity is None:
            return self.nb_drones

        given = self._parse_positive_int(raw_capacity, line_num, "max_drones")
        if given < self.nb_drones:
            self.warnings.add(
                line_num,
                f"{kind} '{zone_name}' max_drones={given} is less than "
                f"nb_drones={self.nb_drones}; overriding to {self.nb_drones}",
            )
            return self.nb_drones
        return given

    def _parse_connection_line(self, line: str, line_num: int) -> None:
        if self.nb_drones is None:
            raise ParseError(line_num, "'nb_drones' must be defined first")

        remainder = line[len("connection:"):]
        mandatory, metadata = self._split_mandatory_and_metadata(
            remainder, line_num, valid_keys=VALID_CONNECTION_METADATA_KEYS
        )

        parts = mandatory.split("-")
        if len(parts) != 2:
            raise ParseError(
                line_num,
                f"Connection must be 'zone_a-zone_b', got '{mandatory}'",
            )
        zone_a, zone_b = parts[0].strip(), parts[1].strip()
        if not zone_a or not zone_b:
            raise ParseError(
                line_num,
                f"Invalid connection format '{mandatory}', "
                f"possibly due to extra dashes",
            )

        if zone_a not in self.zones:
            raise ParseError(
                line_num, f"Connection to undefined zone '{zone_a}'"
            )
        if zone_b not in self.zones:
            raise ParseError(
                line_num, f"Connection to undefined zone '{zone_b}'"
            )

        pair = frozenset({zone_a, zone_b})
        if pair in self._seen_connections:
            raise ParseError(
                line_num,
                f"Duplicate connection between '{zone_a}' and '{zone_b}'",
            )
        self._seen_connections.add(pair)

        raw_capacity = metadata.get("max_link_capacity", "1")
        max_link_capacity = self._parse_positive_int(
            raw_capacity, line_num, "max_link_capacity"
        )

        self.connections.append(
            Connection(
                zone_a=zone_a,
                zone_b=zone_b,
                max_link_capacity=max_link_capacity,
            )
        )

    def _split_mandatory_and_metadata(
        self,
        line: str,
        line_num: int,
        valid_keys: Optional[set[str]] = None,
    ) -> tuple[str, dict[str, str]]:
        if line.endswith("]"):
            close_idx = len(line) - 1
            open_idx = line.rfind("[")

            if open_idx == -1:
                raise ParseError(line_num, "Metadata block missing '['")
            mandatory = line[:open_idx].strip()
            raw_meta = line[open_idx + 1: close_idx]

            metadata = self._parse_metadata(raw_meta, line_num, valid_keys)
            return mandatory, metadata
        return line.strip(), {}

    def _parse_metadata(
        self,
        raw: str,
        line_num: int,
        valid_keys: Optional[set[str]] = None,
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        seen_keys: set[str] = set()

        for token in raw.strip().split():
            if "=" not in token:
                raise ParseError(
                    line_num,
                    f"Invalid metadata token '{token}', expected key=value",
                )
            key, _, value = token.partition("=")
            if not key:
                raise ParseError(
                    line_num, f"Malformed metadata pair '{token}': empty key"
                )
            if not value:
                raise ParseError(
                    line_num,
                    f"Malformed metadata pair '{token}': empty value",
                )

            if key in seen_keys:
                raise ParseError(
                    line_num,
                    f"Duplicate metadata key '{key}' in metadata block",
                )
            seen_keys.add(key)

            if valid_keys is not None and key not in valid_keys:
                raise ParseError(
                    line_num,
                    f"Invalid metadata key '{key}', "
                    f"allowed keys are: {sorted(valid_keys)}",
                )

            if "," in value:
                raise ParseError(
                    line_num,
                    f"Invalid metadata value '{value}', "
                    f"comma found - use spaces instead",
                )

            result[key] = value
        return result

    def _parse_int(self, raw: str, line_num: int, field_name: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise ParseError(
                line_num, f"Invalid {field_name} '{raw}', expected integer"
            )

    def _parse_positive_int(
        self, raw: str, line_num: int, field_name: str
    ) -> int:
        value = self._parse_int(raw, line_num, field_name)
        if value < 1:
            raise ParseError(
                line_num,
                f"{field_name} must be a positive integer, got '{raw}'",
            )
        return value

    def _validate_final_state(self) -> None:
        if self.nb_drones is None:
            raise ParseError(0, "Missing 'nb_drones' definition")
        if not self._has_start:
            raise ParseError(0, "Missing 'start_hub' definition")
        if not self._has_end:
            raise ParseError(0, "Missing 'end_hub' definition")
