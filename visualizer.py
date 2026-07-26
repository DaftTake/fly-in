
import math
import os
from typing import Dict, List, Tuple

import pygame
from models import MoveState, SimConfig, SimulationTurn, Zone
from renderer import TerminalRenderer


COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    "red": (231, 76, 60),
    "orange": (230, 126, 34),
    "yellow": (241, 196, 15),
    "gold": (255, 215, 0),
    "green": (46, 204, 113),
    "lime": (50, 205, 50),
    "blue": (52, 152, 219),
    "cyan": (26, 188, 156),
    "purple": (155, 89, 182),
    "magenta": (255, 0, 255),
    "brown": (139, 69, 19),
    "black": (40, 40, 40),
    "maroon": (128, 0, 0),
    "darkred": (139, 0, 0),
    "violet": (238, 130, 238),
    "crimson": (220, 20, 60),
}


class Visualizer:
    """Pygame GUI visualizer for drone routing."""

    WIDTH = 1440
    HEIGHT = 1080

    def __init__(
        self, config: SimConfig, turns: List[SimulationTurn]
    ) -> None:
        """Initialize visualizer with config and simulation turns."""
        self.config = config
        self.turns = turns
        self.turn_idx = 0
        self.is_playing = False
        self.positions: Dict[str, Tuple[int, int]] = {}
        self.renderer = TerminalRenderer()
        self._calc_positions()

    def _calc_positions(self) -> None:
        """Calculate screen positions for zones."""
        margin_x = 120
        margin_y = 120
        usable_w = self.WIDTH - 2 * margin_x
        usable_h = self.HEIGHT - 2 * margin_y - 100

        xs = [z.x for z in self.config.zones.values()]
        ys = [z.y for z in self.config.zones.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1, max_x - min_x)
        span_y = max(1, max_y - min_y)

        num_zones = len(self.config.zones)
        raw_pos: Dict[str, Tuple[int, int]] = {}

        for idx, (name, z) in enumerate(self.config.zones.items()):
            if span_x == 1 and span_y == 1:
                angle = 2 * math.pi * idx / max(1, num_zones)
                px = int(self.WIDTH / 2 + 350 * math.cos(angle))
                py = int(self.HEIGHT / 2 + 300 * math.sin(angle))
            else:
                px = margin_x + int(((z.x - min_x) / span_x) * usable_w)
                py = margin_y + int(((z.y - min_y) / span_y) * usable_h)
            raw_pos[name] = (px, py)

        self.positions = raw_pos

    def _get_zone_color(self, zone: Zone) -> Tuple[int, int, int]:
        """Get RGB color for a zone."""
        if zone.color and zone.color.lower() in COLOR_MAP:
            return COLOR_MAP[zone.color.lower()]
        if zone.is_start:
            return (46, 204, 113)
        if zone.is_end:
            return (241, 196, 15)
        if zone.zone_type == "restricted":
            return (231, 76, 60)
        if zone.zone_type == "priority":
            return (26, 188, 156)
        if zone.zone_type == "blocked":
            return (127, 140, 141)
        return (52, 152, 219)

    def _get_drone_positions(self) -> Dict[int, Tuple[int, int]]:
        """Calculate active drone screen positions."""
        start_z = next(
            z.name for z in self.config.zones.values() if z.is_start
        )
        base_pos: Dict[int, Tuple[int, int]] = {
            i: self.positions[start_z]
            for i in range(1, self.config.nb_drones + 1)
        }

        for t_idx in range(min(self.turn_idx, len(self.turns))):
            for move in self.turns[t_idx].moves:
                if move.state == MoveState.ARRIVED:
                    base_pos[move.drone_id] = self.positions[move.to_zone]
                elif move.state == MoveState.TRANSIT:
                    p1 = self.positions[move.from_zone]
                    p2 = self.positions[move.to_zone]
                    base_pos[move.drone_id] = (
                        (p1[0] + p2[0]) // 2,
                        (p1[1] + p2[1]) // 2,
                    )

        grouped: Dict[Tuple[int, int], List[int]] = {}
        for d_id, p in base_pos.items():
            grouped.setdefault(p, []).append(d_id)

        offset_pos: Dict[int, Tuple[int, int]] = {}
        for (bx, by), d_ids in grouped.items():
            n = len(d_ids)
            if n == 1:
                offset_pos[d_ids[0]] = (bx, by)
            else:
                cols = math.ceil(math.sqrt(n))
                rows = math.ceil(n / cols)
                for idx, d_id in enumerate(d_ids):
                    c = idx % cols
                    r = idx // cols
                    ox = int((c - (cols - 1) / 2.0) * 22)
                    oy = int((r - (rows - 1) / 2.0) * 22)
                    offset_pos[d_id] = (bx + ox, by + oy)

        return offset_pos

    def _set_turn(self, new_idx: int) -> None:
        """Set simulation turn index and print movement log to terminal."""
        if 0 <= new_idx <= len(self.turns) and new_idx != self.turn_idx:
            self.turn_idx = new_idx
            if self.turn_idx > 0:
                turn_obj = self.turns[self.turn_idx - 1]
                lines = self.renderer.render([turn_obj])
                for line in lines:
                    print(line, flush=True)
            else:
                print("[Reset to Turn 0]", flush=True)

    def run(self) -> None:
        """Run Pygame main loop."""
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Fly-In Visualizer")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("Helvetica", 14, bold=True)
        hud_font = pygame.font.SysFont("Helvetica", 18, bold=True)

        drone_img = None
        if os.path.exists("drone.png"):
            try:
                raw_img = pygame.image.load("drone.png").convert_alpha()
                drone_img = pygame.transform.smoothscale(raw_img, (32, 32))
            except Exception:
                drone_img = None

        running = True
        timer = 0
        while running:
            dt = clock.tick(30)
            timer += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.is_playing = not self.is_playing
                    elif event.key == pygame.K_RIGHT:
                        self._set_turn(self.turn_idx + 1)
                    elif event.key == pygame.K_LEFT:
                        self._set_turn(self.turn_idx - 1)
                    elif event.key == pygame.K_r:
                        self.is_playing = False
                        self._set_turn(0)

            if self.is_playing and timer > 500:
                timer = 0
                if self.turn_idx < len(self.turns):
                    self._set_turn(self.turn_idx + 1)
                else:
                    self.is_playing = False

            screen.fill((30, 30, 35))

            for conn in self.config.connections:
                p1 = self.positions[conn.zone_a]
                p2 = self.positions[conn.zone_b]
                pygame.draw.line(screen, (90, 100, 115), p1, p2, 2)

            sq_size = 36
            for name, zone in self.config.zones.items():
                px, py = self.positions[name]
                color = self._get_zone_color(zone)
                rect = pygame.Rect(
                    px - sq_size // 2, py - sq_size // 2, sq_size, sq_size
                )

                pygame.draw.rect(screen, color, rect, border_radius=8)
                pygame.draw.rect(
                    screen, (20, 20, 25), rect, width=2, border_radius=8
                )

                if zone.is_start or zone.is_end:
                    halo_rect = pygame.Rect(
                        px - (sq_size + 8) // 2,
                        py - (sq_size + 8) // 2,
                        sq_size + 8,
                        sq_size + 8,
                    )
                    pygame.draw.rect(
                        screen, color, halo_rect, width=3, border_radius=10
                    )

            d_positions = self._get_drone_positions()
            for d_id, (dx, dy) in d_positions.items():
                if drone_img:
                    pygame.draw.circle(screen, (255, 255, 255), (dx, dy), 16)
                    pygame.draw.circle(screen, (231, 76, 60), (dx, dy), 16, 2)
                    screen.blit(drone_img, (dx - 16, dy - 16))
                else:
                    pygame.draw.circle(screen, (231, 76, 60), (dx, dy), 12)

                d_txt = font.render(f"D{d_id}", True, (231, 76, 60))
                screen.blit(
                    d_txt, (dx - d_txt.get_width() // 2, dy + 18)
                )

            total_t = len(self.turns)
            hud_bg = pygame.Rect(20, 20, 260, 50)
            pygame.draw.rect(screen, (40, 45, 55), hud_bg, border_radius=8)
            pygame.draw.rect(
                screen, (70, 80, 95), hud_bg, width=2, border_radius=8
            )

            status = "PLAYING" if self.is_playing else "PAUSED"
            hud_text = f"TURN: {self.turn_idx} / {total_t} ({status})"
            hud_surface = hud_font.render(hud_text, True, (46, 204, 113))
            screen.blit(hud_surface, (35, 33))

            info = (
                "[SPACE] Play/Pause | [<- / ->] Step Turn | [R] Reset"
            )
            info_txt = font.render(info, True, (200, 200, 200))
            screen.blit(info_txt, (30, self.HEIGHT - 40))

            pygame.display.flip()

        pygame.quit()
