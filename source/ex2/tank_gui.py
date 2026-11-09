"""Task 2 - Requirement 3: PyGame graphical user interface for the Tank Battle game.

Upgraded Tactical Military Edition:
- Realistic procedural terrain, 3D-shaded destructible brick walls, fortified radar bases,
  and Main Battle Tanks (tracks, sloped ERA hull, polygonal turret, bore evacuator, muzzle brake,
  headlights with light cones, recoil animation).
- Particle effects engine: muzzle flashes, AP tracer shells, explosions, flying debris,
  rising smoke, scorch craters, and persistent tank tread marks.
- Tactical Hangar Mode & Player Selection Screen with live tank previews, quick mode presets
  (Human vs AI, AI vs AI, Human vs Human, Plugin Loader), and full Mouse + Keyboard support.

Run:   python tank_gui.py
       python tank_gui.py --p1 human --p2 "heuristic minimax + alpha"      (skip the menu)
       python tank_gui.py --p1 agents/example_greedy_agent.py --p2 hab

Menu   : UP/DOWN choose player, LEFT/RIGHT change controller, 1-3 quick mode presets,
         Mouse click anywhere, L open a plugin file (or drag & drop a .py file), ENTER start, ESC quit.
In game: arrows / WASD move (human), SPACE fire, X stay, P pause, N single step,
         +/- speed, R rematch, M menu, ESC quit (or click HUD buttons).
"""
import argparse
import math
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

import pygame

from tank_game import (
    Action, Direction, GameConfig, MAX_PLAYER, MIN_PLAYER,
    TANK_HP, BASE_HP, WALL_HP, MAX_CYCLES
)
from arena import GameController
from agent_loader import AgentLoadError, AgentSpec, all_specs, file_spec

# --------------------------------------------------------------------------- layout & palette
CELL = 56
BOARD_PAD = 32
PANEL_W = 430

BG = (14, 17, 22)
PANEL_BG = (20, 24, 31)
CARD_BG = (27, 33, 43)
CARD_ACTIVE = (35, 44, 58)
BORDER_STEEL = (64, 76, 94)
GRID = (42, 48, 38)
TEXT = (238, 242, 248)
MUTED = (148, 160, 178)
AMBER = (248, 192, 58)
DANGER = (242, 82, 72)
EMERALD = (72, 218, 132)

# Player 0 (MAX): NATO Tactical Blue / Cyan-Steel | Player 1 (MIN): Crimson / Soviet Red
P_COLORS = [(65, 155, 255), (240, 80, 75)]
P_DARK = [(26, 66, 124), (128, 30, 30)]
P_LIGHT = [(140, 205, 255), (255, 150, 145)]
P_HULL = [(48, 108, 182), (178, 52, 48)]
P_TURRET = [(68, 138, 222), (212, 68, 64)]
P_NAMES = ["P1 (MAX, Blue)", "P2 (MIN, Red)"]
P_CALLSIGNS = ["ALPHA-1 [MAX]", "BRAVO-2 [MIN]"]

HUMAN_KEYS = {
    pygame.K_UP: Action.MOVE_UP, pygame.K_w: Action.MOVE_UP,
    pygame.K_DOWN: Action.MOVE_DOWN, pygame.K_s: Action.MOVE_DOWN,
    pygame.K_LEFT: Action.MOVE_LEFT, pygame.K_a: Action.MOVE_LEFT,
    pygame.K_RIGHT: Action.MOVE_RIGHT, pygame.K_d: Action.MOVE_RIGHT,
    pygame.K_SPACE: Action.FIRE, pygame.K_x: Action.STAY,
}

DIR_ANGLE = {
    Direction.UP: -90.0,
    Direction.RIGHT: 0.0,
    Direction.DOWN: 90.0,
    Direction.LEFT: 180.0,
}


def short(text: str, n: int = 34) -> str:
    return text if len(text) <= n else text[:n - 1] + "..."


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_angle(a: float, b: float, t: float) -> float:
    diff = (b - a + 180.0) % 360.0 - 180.0
    return a + diff * t


def _load_unicode_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Loads a Unicode-capable system font (supporting full Vietnamese diacritics)."""
    bold_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    reg_candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in (bold_candidates if bold else reg_candidates):
        if os.path.isfile(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                pass
    try:
        return pygame.font.SysFont("arial,helvetica,segoeui,dejavusans", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size + 4)


class Fonts:
    def __init__(self):
        pygame.font.init()
        self.tiny = _load_unicode_font(12, bold=False)
        self.tiny_bold = _load_unicode_font(12, bold=True)
        self.small = _load_unicode_font(14, bold=False)
        self.small_bold = _load_unicode_font(14, bold=True)
        self.normal = _load_unicode_font(16, bold=True)
        self.sub = _load_unicode_font(20, bold=True)
        self.big = _load_unicode_font(30, bold=True)

    def draw(self, surf, text, pos, font=None, color=TEXT, shadow=True, center=False, right=False):
        f = font or self.normal
        rendered = f.render(str(text), True, color)
        x, y = pos
        if center:
            x -= rendered.get_width() // 2
            y -= rendered.get_height() // 2
        elif right:
            x -= rendered.get_width()
        if shadow:
            sh = f.render(str(text), True, (6, 8, 12))
            surf.blit(sh, (x + 1, y + 2))
        surf.blit(rendered, (x, y))
        return rendered.get_rect(topleft=(x, y))


# --------------------------------------------------------------------------- procedural graphics
class BattlefieldAssets:
    """Pre-renders realistic terrain tiles and 3D destructible brick walls for smooth 60 FPS."""

    def __init__(self, cfg: GameConfig):
        self.cfg = cfg
        self.board_w = cfg.width * CELL
        self.board_h = cfg.height * CELL
        self.terrain_surf = self._build_terrain()
        self.wall_surfs = {hp: self._build_wall(hp) for hp in (1, 2, 3)}

    def _build_terrain(self) -> pygame.Surface:
        surf = pygame.Surface((self.board_w, self.board_h))
        rng = random.Random(42)

        for gy in range(self.cfg.height):
            for gx in range(self.cfg.width):
                x0, y0 = gx * CELL, gy * CELL
                parity = (gx + gy) % 2
                base_r = 45 + (3 if parity else 0) + rng.randint(-2, 2)
                base_g = 51 + (3 if parity else 0) + rng.randint(-2, 2)
                base_b = 39 + (2 if parity else 0) + rng.randint(-2, 2)
                pygame.draw.rect(surf, (base_r, base_g, base_b), (x0, y0, CELL, CELL))

                # Soil grain, pebbles, and micro-texture
                for _ in range(30):
                    px = x0 + rng.randint(2, CELL - 3)
                    py = y0 + rng.randint(2, CELL - 3)
                    delta = rng.choice([-8, -5, 4, 7])
                    c = (
                        max(20, min(95, base_r + delta)),
                        max(20, min(95, base_g + delta)),
                        max(18, min(85, base_b + delta)),
                    )
                    if rng.random() < 0.35:
                        pygame.draw.circle(surf, c, (px, py), 1)
                    else:
                        surf.set_at((px, py), c)

                # Small grass tufts on some tiles
                if rng.random() < 0.35:
                    tx = x0 + rng.randint(8, CELL - 9)
                    ty = y0 + rng.randint(8, CELL - 9)
                    for blade in (-2, 0, 2):
                        pygame.draw.line(
                            surf, (58, 78, 46),
                            (tx + blade, ty + 2),
                            (tx + blade + rng.randint(-1, 1), ty - 3), 1
                        )

                # Tactical grid bevel
                pygame.draw.rect(surf, (35, 40, 31), (x0, y0, CELL, CELL), 1)

        # Subtle tactical sector lines
        cx, cy = self.board_w // 2, self.board_h // 2
        pygame.draw.circle(surf, (56, 64, 50), (cx, cy), CELL * 2, 1)
        return surf

    def _build_wall(self, hp: int) -> pygame.Surface:
        surf = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        rng = random.Random(100 + hp * 17)

        # Drop shadow
        pygame.draw.rect(surf, (0, 0, 0, 105), (4, 5, CELL - 4, CELL - 4), border_radius=4)

        margin = 3
        w = CELL - margin * 2
        h = CELL - margin * 2

        # Mortar base
        mortar_col = (52, 48, 44) if hp == 3 else (42, 38, 35) if hp == 2 else (32, 28, 26)
        pygame.draw.rect(surf, mortar_col, (margin, margin, w, h), border_radius=4)

        # Brick pattern (4 rows)
        rows = 4
        row_h = (h - 6) // rows
        for r in range(rows):
            ry = margin + 3 + r * row_h
            offset = 0 if r % 2 == 0 else (w // 4)
            cols = 3 if r % 2 == 0 else 4
            for c in range(cols):
                bx = margin + 3 + c * (w // 3) - (offset if c > 0 else 0)
                bw = (w // 3) - 3 if (c > 0 or r % 2 == 0) else (w // 6)
                bx = max(margin + 3, bx)
                if bx + bw > margin + w - 3:
                    bw = (margin + w - 3) - bx
                if bw <= 3:
                    continue

                if hp == 1 and rng.random() < 0.30:
                    pygame.draw.rect(surf, (24, 22, 20), (bx, ry, bw, row_h - 2))
                    continue

                shade = (170, 90, 56) if hp == 3 else (142, 76, 48) if hp == 2 else (112, 58, 40)
                brick_c = (
                    max(40, min(225, shade[0] + rng.randint(-14, 14))),
                    max(30, min(185, shade[1] + rng.randint(-10, 10))),
                    max(25, min(155, shade[2] + rng.randint(-8, 8))),
                )
                pygame.draw.rect(surf, brick_c, (bx, ry, bw, row_h - 2), border_radius=2)
                hi = (min(255, brick_c[0] + 26), min(255, brick_c[1] + 20), min(255, brick_c[2] + 16))
                pygame.draw.line(surf, hi, (bx + 1, ry), (bx + bw - 2, ry), 1)

        # Steel reinforced frame & corner rivets
        frame_c = (118, 126, 136) if hp == 3 else (88, 94, 102) if hp == 2 else (68, 64, 62)
        pygame.draw.rect(surf, frame_c, (margin, margin, w, h), 2, border_radius=4)
        for rx, ry in [(margin + 3, margin + 3), (margin + w - 4, margin + 3),
                       (margin + 3, margin + h - 4), (margin + w - 4, margin + h - 4)]:
            pygame.draw.circle(surf, (175, 182, 190), (rx, ry), 2)

        # Cracks for damaged states
        if hp <= 2:
            pts1 = [(14, 10), (22, 22), (19, 32), (28, 44)]
            pygame.draw.lines(surf, (20, 16, 14), False, pts1, 2)
        if hp == 1:
            pts2 = [(42, 12), (31, 25), (36, 36), (22, 46)]
            pygame.draw.lines(surf, (16, 12, 10), False, pts2, 3)
            pygame.draw.line(surf, (135, 140, 146), (16, 26), (38, 26), 2)

        return surf


# --------------------------------------------------------------------------- vehicle & base renderer
def draw_realistic_tank(
    surf: pygame.Surface,
    cx: float,
    cy: float,
    angle_deg: float,
    player: int,
    hp: int,
    max_hp: int = TANK_HP,
    recoil: float = 0.0,
    scale: float = 1.0,
    is_active: bool = False,
    treads_phase: float = 0.0,
    show_hp: bool = True,
    turret_offset_deg: float = 0.0,
):
    """Renders a realistic Main Battle Tank centered at (cx, cy) rotated to angle_deg."""
    size = int(76 * scale)
    tank_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    mid = size // 2

    hull_len = int(42 * scale)
    hull_w = int(31 * scale)
    track_w = int(7 * scale)

    # 1. Active tactical target ring under tank
    if is_active:
        pulse = int(3 + 2 * math.sin(pygame.time.get_ticks() * 0.008))
        rad_ring = int(25 * scale) + pulse
        pygame.draw.circle(surf, P_COLORS[player], (int(cx), int(cy)), rad_ring, 2)

    # 2. Soft drop shadow
    sh_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(
        sh_surf, (0, 0, 0, 115),
        (mid - hull_len // 2 - 2, mid - hull_w // 2 - 2, hull_len + 4, hull_w + 4),
        border_radius=int(6 * scale)
    )
    rot_sh = pygame.transform.rotate(sh_surf, -angle_deg)
    surf.blit(rot_sh, rot_sh.get_rect(center=(int(cx) + 3, int(cy) + 4)))

    # 3. Left & Right Heavy Caterpillar Tracks (oriented pointing RIGHT = 0 deg)
    left_tr = pygame.Rect(mid - hull_len // 2, mid - hull_w // 2, hull_len, track_w)
    right_tr = pygame.Rect(mid - hull_len // 2, mid + hull_w // 2 - track_w, hull_len, track_w)
    for tr in (left_tr, right_tr):
        pygame.draw.rect(tank_surf, (28, 31, 35), tr, border_radius=int(2 * scale))
        pygame.draw.rect(tank_surf, (62, 68, 76), tr, 1, border_radius=int(2 * scale))
        step = max(4, int(5 * scale))
        offset = int(treads_phase) % step
        for tx in range(tr.left + 2 + offset, tr.right - 2, step):
            pygame.draw.line(tank_surf, (86, 92, 102), (tx, tr.top + 1), (tx, tr.bottom - 2), 2)
        # Front & rear armored track mudguards
        pygame.draw.rect(
            tank_surf, P_DARK[player],
            (tr.right - int(5 * scale), tr.top, int(5 * scale), tr.height),
            border_radius=1
        )
        pygame.draw.rect(
            tank_surf, P_DARK[player],
            (tr.left, tr.top, int(4 * scale), tr.height),
            border_radius=1
        )

    # 4. Sloped Armored Hull Body (Chobham / ERA armor styling)
    body_rect = pygame.Rect(
        mid - hull_len // 2 + int(2 * scale),
        mid - hull_w // 2 + track_w - 1,
        hull_len - int(5 * scale),
        hull_w - 2 * track_w + 2
    )
    pygame.draw.rect(tank_surf, P_DARK[player], body_rect, border_radius=int(4 * scale))
    inner_hull = body_rect.inflate(-int(4 * scale), -int(4 * scale))
    pygame.draw.rect(tank_surf, P_HULL[player], inner_hull, border_radius=int(3 * scale))

    # Rear engine deck twin radiator grilles
    grille_x = inner_hull.left + int(2 * scale)
    grille_w = int(8 * scale)
    for gy_off in (inner_hull.top + 2, inner_hull.centery + 1):
        g_rect = pygame.Rect(grille_x, gy_off, grille_w, max(3, inner_hull.height // 2 - 3))
        pygame.draw.rect(tank_surf, (24, 28, 34), g_rect, border_radius=1)
        for lx in range(g_rect.left + 2, g_rect.right - 1, max(2, int(2 * scale))):
            pygame.draw.line(tank_surf, (52, 58, 66), (lx, g_rect.top + 1), (lx, g_rect.bottom - 1), 1)

    # Front sloped glacis armor V-chevron & headlights
    pygame.draw.line(
        tank_surf, P_LIGHT[player],
        (inner_hull.right - 2, inner_hull.top + 2),
        (inner_hull.right - 2, inner_hull.bottom - 2), max(1, int(2 * scale))
    )
    pygame.draw.lines(
        tank_surf, P_DARK[player], False,
        [
            (inner_hull.right - int(8 * scale), inner_hull.top + 2),
            (inner_hull.right - int(3 * scale), inner_hull.centery),
            (inner_hull.right - int(8 * scale), inner_hull.bottom - 2),
        ],
        max(1, int(1.5 * scale))
    )
    for hly in (body_rect.top + int(2 * scale), body_rect.bottom - int(3 * scale)):
        pygame.draw.circle(tank_surf, (255, 248, 195), (body_rect.right, hly), max(1, int(2 * scale)))

    # Rotate hull + tracks composite
    rot_hull = pygame.transform.rotate(tank_surf, -angle_deg)
    surf.blit(rot_hull, rot_hull.get_rect(center=(int(cx), int(cy))))

    # 5. Polygonal Composite Turret & Rifled 120mm Cannon (supports independent turret offset)
    turret_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rec_px = int(recoil * 7 * scale)
    barrel_len = int(28 * scale) - rec_px
    barrel_thick = max(4, int(5 * scale))

    # Main gun tube
    barrel_rect = pygame.Rect(mid, mid - barrel_thick // 2, barrel_len, barrel_thick)
    pygame.draw.rect(turret_surf, (54, 60, 70), barrel_rect)
    pygame.draw.line(
        turret_surf, (165, 178, 195),
        (mid, mid - 1), (mid + barrel_len - 2, mid - 1), max(1, int(1.5 * scale))
    )
    # Bore evacuator (fume extractor bulge mid-barrel)
    evac_rect = pygame.Rect(
        mid + int(12 * scale) - rec_px // 2,
        mid - barrel_thick // 2 - 1,
        int(6 * scale),
        barrel_thick + 2
    )
    pygame.draw.rect(turret_surf, (78, 86, 98), evac_rect, border_radius=2)
    pygame.draw.rect(turret_surf, (135, 145, 160), evac_rect, 1, border_radius=2)

    # Muzzle brake at barrel tip
    mb_w = max(4, int(5 * scale))
    mb_h = max(6, int(8 * scale))
    mb_rect = pygame.Rect(mid + barrel_len - mb_w // 2, mid - mb_h // 2, mb_w, mb_h)
    pygame.draw.rect(turret_surf, (68, 76, 88), mb_rect, border_radius=1)
    pygame.draw.rect(turret_surf, (190, 200, 215), mb_rect, 1, border_radius=1)

    # Polygonal M1/Leopard style angled turret
    tx_back = mid - int(13 * scale)
    tx_mid = mid - int(3 * scale)
    tx_front = mid + int(8 * scale)
    ty_wide = int(10 * scale)
    ty_narrow = int(6 * scale)
    turret_poly = [
        (tx_back, mid - ty_narrow),
        (tx_mid, mid - ty_wide),
        (tx_front, mid - ty_narrow),
        (tx_front, mid + ty_narrow),
        (tx_mid, mid + ty_wide),
        (tx_back, mid + ty_narrow),
    ]
    pygame.draw.polygon(turret_surf, P_TURRET[player], turret_poly)
    pygame.draw.polygon(turret_surf, P_LIGHT[player], turret_poly, max(1, int(1.8 * scale)))

    # Gun mantlet block
    mantlet_rect = pygame.Rect(
        mid + int(5 * scale) - rec_px // 3,
        mid - int(4 * scale),
        int(6 * scale),
        int(8 * scale)
    )
    pygame.draw.rect(turret_surf, P_DARK[player], mantlet_rect, border_radius=2)
    pygame.draw.rect(turret_surf, P_LIGHT[player], mantlet_rect, 1, border_radius=2)

    # Commander's Cupola & CITV Thermal Sight
    cupola_pos = (mid - int(4 * scale), mid - int(3 * scale))
    pygame.draw.circle(turret_surf, P_DARK[player], cupola_pos, max(3, int(4 * scale)))
    pygame.draw.circle(turret_surf, (195, 210, 228), cupola_pos, max(2, int(2.5 * scale)))
    pygame.draw.rect(
        turret_surf, P_DARK[player],
        (mid - int(5 * scale), mid + int(2 * scale), int(5 * scale), int(4 * scale)),
        border_radius=1
    )

    rot_turret = pygame.transform.rotate(turret_surf, -(angle_deg + turret_offset_deg))
    surf.blit(rot_turret, rot_turret.get_rect(center=(int(cx), int(cy))))

    # 6. Overhead segmented tactical HP bar
    if show_hp and hp > 0:
        bw = int(40 * scale)
        bh = 5
        bx = int(cx) - bw // 2
        by = int(cy) - int(27 * scale)
        pygame.draw.rect(surf, (10, 13, 18), (bx - 1, by - 1, bw + 2, bh + 2), border_radius=2)
        seg_w = bw / max_hp
        hp_col = EMERALD if hp >= 4 else AMBER if hp >= 2 else DANGER
        for s_idx in range(hp):
            sx = int(bx + s_idx * seg_w)
            sw = max(2, int(seg_w) - 1)
            pygame.draw.rect(surf, hp_col, (sx, by, sw, bh))


def draw_realistic_base(
    surf: pygame.Surface,
    rect: Tuple[int, int, int, int],
    player: int,
    hp: int,
    fonts: Fonts,
    max_hp: int = BASE_HP,
):
    """Renders a fortified military headquarters bunker with rotating radar dish and shield bar."""
    x, y, w, h = rect
    cx, cy = x + w // 2, y + h // 2
    t = pygame.time.get_ticks() * 0.003

    # Drop shadow
    pygame.draw.rect(surf, (12, 14, 12), (x + 5, y + 6, w - 6, h - 6), border_radius=8)

    # Outer sandbag / concrete perimeter
    pygame.draw.rect(surf, (78, 84, 76), (x + 3, y + 3, w - 6, h - 6), border_radius=7)
    pygame.draw.rect(surf, (116, 124, 114), (x + 3, y + 3, w - 6, h - 6), 2, border_radius=7)

    # Corner defensive bastions
    for bx, by in [(x + 5, y + 5), (x + w - 11, y + 5), (x + 5, y + h - 11), (x + w - 11, y + h - 11)]:
        pygame.draw.rect(surf, (98, 106, 96), (bx, by, 6, 6), border_radius=2)

    # Faction armored command pad
    inner = (x + 8, y + 8, w - 16, h - 16)
    pygame.draw.rect(surf, P_DARK[player], inner, border_radius=5)
    pygame.draw.rect(surf, P_COLORS[player], inner, 2, border_radius=5)

    # Tactical crosshairs on roof
    pygame.draw.line(surf, P_HULL[player], (cx - 12, cy), (cx + 12, cy), 1)
    pygame.draw.line(surf, P_HULL[player], (cx, cy - 12), (cx, cy + 12), 1)

    # Armored Command Dome
    pygame.draw.circle(surf, (38, 44, 54), (cx, cy), 13)
    pygame.draw.circle(surf, P_LIGHT[player], (cx, cy), 13, 2)

    # Rotating Radar Dish sweep
    angle = t + (0 if player == 0 else math.pi)
    rx = cx + int(math.cos(angle) * 10)
    ry = cy + int(math.sin(angle) * 10)
    pygame.draw.line(surf, (235, 245, 255), (cx, cy), (rx, ry), 2)
    perp_x = int(-math.sin(angle) * 5)
    perp_y = int(math.cos(angle) * 5)
    pygame.draw.line(surf, P_LIGHT[player], (rx - perp_x, ry - perp_y), (rx + perp_x, ry + perp_y), 2)
    pygame.draw.circle(surf, (255, 255, 255), (cx, cy), 3)

    # HQ HP Bar at bottom of tile
    bw = w - 12
    bh = 5
    bx = x + 6
    by = y + h - 8
    pygame.draw.rect(surf, (10, 13, 18), (bx - 1, by - 1, bw + 2, bh + 2), border_radius=2)
    if hp > 0:
        fill_w = max(2, int(bw * hp / max_hp))
        col = P_LIGHT[player] if hp > 3 else DANGER
        pygame.draw.rect(surf, col, (bx, by, fill_w, bh), border_radius=1)

    fonts.draw(surf, f"HQ:{hp}", (cx, y + 9), fonts.tiny_bold, (250, 250, 255), center=True)


# --------------------------------------------------------------------------- vector icon helpers
def draw_chevron(surf: pygame.Surface, center: Tuple[int, int], direction: int, color=TEXT):
    """Draws a crisp left (-1) or right (+1) triangle chevron icon."""
    cx, cy = center
    pts = [
        (cx + direction * 5, cy),
        (cx - direction * 4, cy - 6),
        (cx - direction * 4, cy + 6),
    ]
    pygame.draw.polygon(surf, color, pts)


# --------------------------------------------------------------------------- particle & VFX system
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "fade_smoke", "gravity")

    def __init__(self, x, y, vx, vy, life, size, color, fade_smoke=False, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.fade_smoke = fade_smoke
        self.gravity = gravity

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= dt
        return self.life > 0


class Shockwave:
    __slots__ = ("x", "y", "radius", "max_radius", "life", "max_life", "color", "width")

    def __init__(self, x, y, max_radius, life, color=(255, 195, 90), width=3):
        self.x = x
        self.y = y
        self.radius = 4.0
        self.max_radius = max_radius
        self.life = life
        self.max_life = life
        self.color = color
        self.width = width

    def update(self, dt: float) -> bool:
        self.life -= dt
        progress = 1.0 - max(0.0, self.life / self.max_life)
        self.radius = 4.0 + (self.max_radius - 4.0) * (1.0 - (1.0 - progress) ** 2)
        return self.life > 0


class TracerStreak:
    """Visualizes high-velocity AP shell trajectory across cells."""
    __slots__ = ("x0", "y0", "x1", "y1", "color", "life", "max_life")

    def __init__(self, x0, y0, x1, y1, color, life=0.35):
        self.x0, self.y0 = x0, y0
        self.x1, self.y1 = x1, y1
        self.color = color
        self.life = life
        self.max_life = life

    def update(self, dt: float) -> bool:
        self.life -= dt
        return self.life > 0


# ----------------------------------------------------------------------------- menu
class MenuScreen:
    """Tactical Command Hangar & Mode Selection Screen."""

    MODES = [
        ("1. CHIẾN DỊCH (HUMAN vs AI)", "human_ai"),
        ("2. ĐẤU TRƯỜNG AI (AI vs AI)", "ai_ai"),
        ("3. ĐỐI KHÁNG (2 PLAYERS)", "human_human"),
        ("4. NẠP PLUGIN (.PY)", "load_plugin"),
    ]

    def __init__(self, specs: List[AgentSpec], fonts: Fonts):
        self.specs = specs
        self.fonts = fonts
        self.row = 0
        default2 = next(
            (i for i, s in enumerate(specs) if "Heuristic Minimax + Alpha" in s.label),
            min(1, len(specs) - 1)
        )
        self.sel = [0, default2]
        self.message = "Sẵn sàng triển khai lực lượng. Chọn chế độ hoặc tùy chỉnh từng xe tăng."
        self.msg_color = EMERALD
        self.click_zones: List[Tuple[pygame.Rect, str, object]] = []
        self.hover_action = None
        self.dust_particles = [
            [
                random.uniform(0, 1220),
                random.uniform(0, 800),
                random.uniform(-12, 12),
                random.uniform(-18, -5),
                random.uniform(1, 3),
            ]
            for _ in range(45)
        ]

    def apply_preset(self, preset_key: str):
        human_idx = next((i for i, s in enumerate(self.specs) if s.is_human), 0)
        hab_idx = next(
            (i for i, s in enumerate(self.specs) if "Heuristic Minimax + Alpha" in s.label),
            min(1, len(self.specs) - 1)
        )
        other_ai_idx = next(
            (i for i, s in enumerate(self.specs) if not s.is_human and i != hab_idx),
            hab_idx
        )
        if preset_key == "human_ai":
            self.sel = [human_idx, hab_idx]
            self.message = "Đã chọn chế độ: Người chơi (P1) đấu với AI Chiến thuật (P2)"
            self.msg_color = P_LIGHT[0]
        elif preset_key == "ai_ai":
            self.sel = [hab_idx, other_ai_idx]
            self.message = "Đã chọn chế độ: Giả lập Đấu trường AI vs AI"
            self.msg_color = AMBER
        elif preset_key == "human_human":
            self.sel = [human_idx, human_idx]
            self.message = "Đã chọn chế độ: Đối kháng 2 Người chơi trên cùng bàn phím"
            self.msg_color = EMERALD
        elif preset_key == "load_plugin":
            self.open_file_dialog()

    def add_plugin(self, path):
        try:
            spec = file_spec(path)
        except AgentLoadError as e:
            self.message = f"Lỗi nạp plugin: {e}"
            self.msg_color = DANGER
            return
        self.specs.append(spec)
        self.sel[self.row] = len(self.specs) - 1
        self.message = f"Đã nạp thành công {spec.label} cho {P_NAMES[self.row]}"
        self.msg_color = EMERALD

    def open_file_dialog(self):
        try:
            import tkinter
            from tkinter import filedialog
            root = tkinter.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(filetypes=[("Python agent", "*.py")])
            root.destroy()
        except Exception:
            self.message = "Kéo & thả trực tiếp file .py vào cửa sổ này để nạp thuật toán!"
            self.msg_color = AMBER
            return
        if path:
            self.add_plugin(path)

    def _spec_details(self, spec: AgentSpec) -> Tuple[str, str, int, int, int]:
        """Returns (role_badge, description, intelligence_rating, speed_rating, aggression_rating)."""
        lbl = spec.label.lower()
        if spec.is_human:
            return ("HUMAN COMMANDER", "Điều khiển trực tiếp qua bàn phím (WASD / Mũi tên + SPACE).", 5, 5, 5)
        if "[plugin]" in lbl:
            return ("CUSTOM AI PLUGIN", f"Thuật toán độc lập nạp từ file: {os.path.basename(spec.path or '')}", 4, 4, 5)
        if "heuristic minimax + alpha" in lbl:
            return ("ELITE TACTICAL AI", "Cắt tỉa Alpha-Beta kết hợp hàm đánh giá Heuristic đa mục tiêu.", 5, 4, 5)
        if "heuristic minimax" in lbl:
            return ("TACTICAL AI", "Tìm kiếm Minimax giới hạn độ sâu với hàm lượng giá chiến trường.", 4, 3, 4)
        if "alpha-beta" in lbl:
            return ("SEARCH AI", "Tìm kiếm đối kháng Alpha-Beta cổ điển tối ưu nhánh duyệt.", 3, 4, 3)
        if "minimax" in lbl:
            return ("CLASSIC AI", "Cây trò chơi Minimax chuẩn (Duyệt toàn bộ trạng thái).", 3, 2, 3)
        return ("RECON DRONE AI", "Di chuyển và khai hỏa ngẫu nhiên trên các nước đi hợp lệ.", 1, 5, 2)

    def handle(self, event):
        if event.type == pygame.DROPFILE:
            self.add_plugin(event.file)
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hover_action = None
            for rect, act, payload in self.click_zones:
                if rect.collidepoint(mx, my):
                    self.hover_action = (act, payload)
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for rect, act, payload in self.click_zones:
                if rect.collidepoint(mx, my):
                    if act == "preset":
                        self.apply_preset(payload)
                    elif act == "select_row":
                        self.row = int(payload)
                    elif act == "prev":
                        r = int(payload)
                        self.row = r
                        self.sel[r] = (self.sel[r] - 1) % len(self.specs)
                    elif act == "next":
                        r = int(payload)
                        self.row = r
                        self.sel[r] = (self.sel[r] + 1) % len(self.specs)
                    elif act == "pick_spec":
                        r, idx = payload
                        self.row = r
                        self.sel[r] = idx
                    elif act == "swap":
                        self.sel[0], self.sel[1] = self.sel[1], self.sel[0]
                        self.message = "Đã đổi bên chỉ huy giữa P1 (MAX) và P2 (MIN)."
                        self.msg_color = AMBER
                    elif act == "start":
                        return ("start", self.specs[self.sel[0]], self.specs[self.sel[1]])
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                self.row = 1 - self.row
            elif event.key == pygame.K_LEFT:
                self.sel[self.row] = (self.sel[self.row] - 1) % len(self.specs)
            elif event.key == pygame.K_RIGHT:
                self.sel[self.row] = (self.sel[self.row] + 1) % len(self.specs)
            elif event.key == pygame.K_1:
                self.apply_preset("human_ai")
            elif event.key == pygame.K_2:
                self.apply_preset("ai_ai")
            elif event.key == pygame.K_3:
                self.apply_preset("human_human")
            elif event.key in (pygame.K_l, pygame.K_4):
                self.open_file_dialog()
            elif event.key == pygame.K_s:
                self.sel[0], self.sel[1] = self.sel[1], self.sel[0]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return ("start", self.specs[self.sel[0]], self.specs[self.sel[1]])
        return None

    def draw(self, screen: pygame.Surface):
        f = self.fonts
        w, h = screen.get_size()
        t = pygame.time.get_ticks() / 1000.0
        self.click_zones.clear()

        # 1. Tactical Radar & Hangar Background
        screen.fill((12, 15, 21))
        grid_step = 48
        for gx in range(0, w, grid_step):
            pygame.draw.line(screen, (19, 25, 33), (gx, 0), (gx, h), 1)
        for gy in range(0, h, grid_step):
            pygame.draw.line(screen, (19, 25, 33), (0, gy), (w, gy), 1)

        rcx, rcy = w // 2, h // 2 + 20
        for rad in (140, 260, 380):
            pygame.draw.circle(screen, (22, 32, 42), (rcx, rcy), rad, 1)
        sweep_a = t * 0.9
        sx = rcx + int(math.cos(sweep_a) * 380)
        sy = rcy + int(math.sin(sweep_a) * 380)
        pygame.draw.line(screen, (28, 54, 64), (rcx, rcy), (sx, sy), 2)

        for p in self.dust_particles:
            p[0] = (p[0] + p[2] * 0.03) % w
            p[1] = (p[1] + p[3] * 0.03) % h
            pygame.draw.circle(screen, (48, 58, 72), (int(p[0]), int(p[1])), int(p[4]))

        # 2. Top Command Header Banner
        pygame.draw.rect(screen, (19, 24, 33), (0, 0, w, 92))
        pygame.draw.line(screen, BORDER_STEEL, (0, 92), (w, 92), 2)
        for hx in range(-20, w, 28):
            pygame.draw.polygon(
                screen, (44, 50, 32),
                [(hx, 0), (hx + 14, 0), (hx + 6, 8), (hx - 8, 8)]
            )

        f.draw(screen, "TANK BATTLE // TACTICAL COMMAND CENTER", (36, 18), f.big, TEXT)
        f.draw(
            screen,
            "HỆ THỐNG MÔ PHỎNG CHIẾN THUẬT ĐỐI KHÁNG ZERO-SUM  |  CHỌN CHẾ ĐỘ & LỰC LƯỢNG THAM CHIẾN",
            (38, 60), f.small_bold, AMBER
        )

        # 3. Quick Mode Preset Bar (4 Tactical Mode Cards)
        preset_y = 108
        margin_x = 36
        gap = 14
        card_w = (w - margin_x * 2 - gap * 3) // 4
        card_h = 46

        cur_mode = (
            "human_ai" if (self.specs[self.sel[0]].is_human and not self.specs[self.sel[1]].is_human)
            else "human_human" if (self.specs[self.sel[0]].is_human and self.specs[self.sel[1]].is_human)
            else "ai_ai" if (not self.specs[self.sel[0]].is_human and not self.specs[self.sel[1]].is_human)
            else ""
        )

        for idx, (m_label, m_key) in enumerate(self.MODES):
            rx = margin_x + idx * (card_w + gap)
            rect = pygame.Rect(rx, preset_y, card_w, card_h)
            is_hovered = self.hover_action == ("preset", m_key)
            is_selected = (m_key == cur_mode)
            bg_c = (44, 58, 78) if is_selected else (36, 44, 58) if is_hovered else (25, 31, 41)
            bd_c = AMBER if is_selected else P_LIGHT[0] if is_hovered else BORDER_STEEL
            pygame.draw.rect(screen, bg_c, rect, border_radius=6)
            pygame.draw.rect(screen, bd_c, rect, 2 if is_selected or is_hovered else 1, border_radius=6)
            f.draw(
                screen, m_label,
                (rect.centerx, rect.centery),
                f.small_bold, AMBER if is_selected else TEXT, center=True
            )
            self.click_zones.append((rect, "preset", m_key))

        # 4. Dual Armored Hangar Bays (Player 1 Left vs Player 2 Right)
        bay_y = 170
        bay_h = 445
        bay_w = (w - margin_x * 2 - 76) // 2
        bay_xs = [margin_x, w - margin_x - bay_w]

        for i in range(2):
            bx = bay_xs[i]
            bay_rect = pygame.Rect(bx, bay_y, bay_w, bay_h)
            active = (self.row == i)
            spec = self.specs[self.sel[i]]
            role_badge, desc, r_int, r_spd, r_agg = self._spec_details(spec)

            pygame.draw.rect(screen, (22, 27, 36) if not active else (27, 34, 46), bay_rect, border_radius=10)
            pygame.draw.rect(
                screen, P_COLORS[i] if active else (52, 62, 78),
                bay_rect, 3 if active else 1, border_radius=10
            )
            self.click_zones.append((bay_rect, "select_row", i))

            # Top Faction Header Strip inside Hangar
            header_rect = pygame.Rect(bx + 3, bay_y + 3, bay_w - 6, 46)
            pygame.draw.rect(screen, P_DARK[i], header_rect, border_radius=8)
            f.draw(screen, P_CALLSIGNS[i], (bx + 18, bay_y + 8), f.sub, P_LIGHT[i])
            f.draw(screen, P_NAMES[i], (bx + 18, bay_y + 31), f.tiny_bold, TEXT)

            # Role Badge Pill
            pill_w = 162
            pill_rect = pygame.Rect(bx + bay_w - pill_w - 14, bay_y + 12, pill_w, 26)
            pygame.draw.rect(screen, (16, 20, 28), pill_rect, border_radius=13)
            pygame.draw.rect(screen, P_LIGHT[i], pill_rect, 1, border_radius=13)
            f.draw(screen, role_badge, pill_rect.center, f.tiny_bold, P_LIGHT[i], center=True)

            # Live Rotating Tank Turntable Preview Box
            stage_rect = pygame.Rect(bx + 18, bay_y + 60, 175, 135)
            pygame.draw.rect(screen, (15, 19, 25), stage_rect, border_radius=8)
            pygame.draw.rect(screen, (45, 55, 70), stage_rect, 1, border_radius=8)
            scx, scy = stage_rect.centerx, stage_rect.centery - 6
            pygame.draw.circle(screen, (26, 34, 44), (scx, scy), 48)
            pygame.draw.circle(screen, P_DARK[i], (scx, scy), 48, 2)
            pygame.draw.circle(screen, (38, 48, 62), (scx, scy), 34, 1)

            preview_angle = (-35.0 if i == 0 else 145.0) + math.sin(t * 0.9 + i * 2.0) * 14.0
            turret_scan = math.sin(t * 2.1 + i) * 22.0
            draw_realistic_tank(
                screen, scx, scy, preview_angle, i, TANK_HP,
                scale=1.22, is_active=active, treads_phase=t * 15.0,
                show_hp=False, turret_offset_deg=turret_scan
            )
            f.draw(
                screen,
                "VỊ TRÍ: PHÍA NAM (MAX)" if i == 0 else "VỊ TRÍ: PHÍA BẮC (MIN)",
                (scx, stage_rect.bottom - 12), f.tiny, MUTED, center=True
            )

            # Tactical Spec Gauges
            gx0 = stage_rect.right + 18
            gy0 = bay_y + 64
            gw = bay_w - (stage_rect.width + 54)
            stats_rows = [
                ("TRÍ TUỆ CHIẾN THUẬT", r_int, P_LIGHT[i]),
                ("TỐC ĐỘ PHẢN XẠ", r_spd, EMERALD),
                ("CƯỜNG ĐỘ HỎA LỰC", r_agg, AMBER),
            ]
            for s_idx, (s_name, s_val, s_col) in enumerate(stats_rows):
                ry = gy0 + s_idx * 34
                f.draw(screen, s_name, (gx0, ry), f.tiny_bold, MUTED)
                bar_y = ry + 16
                seg_w = (gw - 20) // 5
                for b_i in range(5):
                    s_rect = pygame.Rect(gx0 + b_i * (seg_w + 4), bar_y, seg_w, 8)
                    pygame.draw.rect(
                        screen, s_col if b_i < s_val else (36, 42, 54),
                        s_rect, border_radius=2
                    )

            f.draw(screen, short(desc, 48), (gx0, gy0 + 106), f.tiny, (195, 205, 220))

            # Selector Carousel Bar (<  Controller Name  >)
            sel_y = bay_y + 206
            btn_prev = pygame.Rect(bx + 18, sel_y, 42, 40)
            btn_next = pygame.Rect(bx + bay_w - 60, sel_y, 42, 40)
            mid_box = pygame.Rect(bx + 66, sel_y, bay_w - 132, 40)

            for btn, tag, dir_sign in [(btn_prev, "prev", -1), (btn_next, "next", 1)]:
                hov = self.hover_action == (tag, i)
                pygame.draw.rect(screen, P_COLORS[i] if hov else (38, 46, 60), btn, border_radius=6)
                pygame.draw.rect(screen, P_LIGHT[i] if hov else BORDER_STEEL, btn, 1, border_radius=6)
                draw_chevron(screen, btn.center, dir_sign, TEXT)
                self.click_zones.append((btn, tag, i))

            pygame.draw.rect(screen, (16, 20, 27), mid_box, border_radius=6)
            pygame.draw.rect(screen, P_COLORS[i] if active else BORDER_STEEL, mid_box, 2 if active else 1, border_radius=6)
            f.draw(screen, short(spec.label, 34), mid_box.center, f.normal, TEXT, center=True)

            # Direct Clickable Algorithm List inside Hangar
            f.draw(screen, "DANH SÁCH ĐIỀU KHIỂN / THUẬT TOÁN (CLICK ĐỂ CHỌN):", (bx + 18, sel_y + 50), f.tiny_bold, MUTED)
            list_y = sel_y + 68
            cols = 2
            chip_w = (bay_w - 44) // cols
            chip_h = 28
            for sp_idx, sp in enumerate(self.specs[:10]):
                c_col = sp_idx % cols
                c_row = sp_idx // cols
                cx_chip = bx + 18 + c_col * (chip_w + 8)
                cy_chip = list_y + c_row * (chip_h + 6)
                chip_rect = pygame.Rect(cx_chip, cy_chip, chip_w, chip_h)
                chosen = (self.sel[i] == sp_idx)
                hov = self.hover_action == ("pick_spec", (i, sp_idx))
                c_bg = P_DARK[i] if chosen else (36, 44, 58) if hov else (25, 30, 40)
                c_bd = P_LIGHT[i] if chosen else P_COLORS[i] if hov else (48, 56, 70)
                pygame.draw.rect(screen, c_bg, chip_rect, border_radius=5)
                pygame.draw.rect(screen, c_bd, chip_rect, 2 if chosen else 1, border_radius=5)
                f.draw(
                    screen, short(sp.label, 25),
                    chip_rect.center, f.tiny_bold if chosen else f.tiny,
                    TEXT if chosen else (185, 195, 210), center=True
                )
                self.click_zones.append((chip_rect, "pick_spec", (i, sp_idx)))

        # Center VS Emblem & Swap Sides Button
        vs_cx = w // 2
        vs_cy = bay_y + bay_h // 2 - 20
        pygame.draw.circle(screen, (26, 32, 44), (vs_cx, vs_cy), 28)
        pygame.draw.circle(screen, AMBER, (vs_cx, vs_cy), 28, 2)
        f.draw(screen, "VS", (vs_cx, vs_cy), f.sub, AMBER, center=True)

        swap_rect = pygame.Rect(vs_cx - 32, vs_cy + 40, 64, 30)
        swap_hov = self.hover_action == ("swap", None)
        pygame.draw.rect(screen, (42, 52, 68) if swap_hov else (28, 34, 46), swap_rect, border_radius=6)
        pygame.draw.rect(screen, AMBER if swap_hov else BORDER_STEEL, swap_rect, 1, border_radius=6)
        f.draw(screen, "ĐỔI BÊN", swap_rect.center, f.tiny_bold, TEXT, center=True)
        self.click_zones.append((swap_rect, "swap", None))

        # 5. Bottom Launch Console & Status Bar
        footer_y = 630
        start_w = 400
        start_h = 56
        start_rect = pygame.Rect(w // 2 - start_w // 2, footer_y, start_w, start_h)
        start_hov = self.hover_action == ("start", None)
        pygame.draw.rect(
            screen,
            (52, 168, 95) if start_hov else (38, 138, 76),
            start_rect, border_radius=8
        )
        pygame.draw.rect(screen, (140, 250, 175), start_rect, 2, border_radius=8)
        draw_chevron(screen, (start_rect.left + 44, start_rect.centery), 1, (255, 255, 255))
        f.draw(
            screen, "BẮT ĐẦU TRẬN ĐẤU  [ENTER]",
            (start_rect.centerx + 10, start_rect.centery), f.sub, (255, 255, 255), center=True
        )
        self.click_zones.append((start_rect, "start", None))

        # Status & Keyboard Hint Footer
        f.draw(screen, short(self.message, 95), (w // 2, footer_y + 74), f.small_bold, self.msg_color, center=True)
        help_text = (
            "PHÍM TẮT:  [Lên/Xuống/TAB] Đổi bên   [Trái/Phải] Đổi thuật toán   [1-3] Chế độ nhanh   "
            "[S] Đổi vị trí   [L] Nạp file .py   [ENTER] Khai chiến   [ESC] Thoát"
        )
        f.draw(screen, help_text, (w // 2, footer_y + 100), f.tiny, MUTED, center=True)


# ----------------------------------------------------------------------------- game
class GameScreen:
    """Realistic Battlefield & C4ISR Tactical Telemetry HUD."""

    def __init__(self, spec0: AgentSpec, spec1: AgentSpec, fonts: Fonts, delay=0.25):
        self.specs = (spec0, spec1)
        self.fonts = fonts
        self.delay = delay
        self.cfg = GameConfig()
        self.assets = BattlefieldAssets(self.cfg)
        self.hud_buttons: List[Tuple[pygame.Rect, str]] = []
        self.hover_btn: Optional[str] = None
        self.new_game()

    def new_game(self):
        a0, a1 = self.specs[0].create(), self.specs[1].create()
        self.ctrl = GameController(a0, a1, self.specs[0].label, self.specs[1].label,
                                   time_limit=3.0)
        self.paused = False
        self.step_once = False
        self.last_apply = 0.0
        self.last_frame_time = pygame.time.get_ticks() / 1000.0
        self.flashes: Dict[Tuple[int, int], int] = {}
        self.cfg = self.ctrl.state.cfg

        # Smooth visual interpolation states for tanks
        self.vis_pos = [
            [float(t.pos[0]), float(t.pos[1])] for t in self.ctrl.state.tanks
        ]
        self.vis_angle = [
            DIR_ANGLE[t.facing] for t in self.ctrl.state.tanks
        ]
        self.recoil = [0.0, 0.0]
        self.tread_phase = [0.0, 0.0]

        # Battlefield persistent decals & VFX
        self.tread_marks: List[Tuple[float, float, float, int]] = []
        self.craters: List[Tuple[int, int, int]] = []
        self.particles: List[Particle] = []
        self.shockwaves: List[Shockwave] = []
        self.tracers: List[TracerStreak] = []
        self.combat_log: List[Tuple[str, Tuple[int, int, int]]] = [
            ("Hệ thống chiến trường đã kích hoạt.", EMERALD),
        ]
        self.screen_shake = 0.0

    # ---- helpers & VFX spawners
    def _board_px(self, gx: float, gy: float) -> Tuple[float, float]:
        return (BOARD_PAD + gx * CELL + CELL / 2.0, BOARD_PAD + gy * CELL + CELL / 2.0)

    def _spawn_muzzle_flash(self, player: int, pos: Tuple[int, int], facing: Direction):
        cx, cy = self._board_px(pos[0], pos[1])
        dx, dy = facing.value
        mx = cx + dx * (CELL * 0.48)
        my = cy + dy * (CELL * 0.48)
        self.shockwaves.append(Shockwave(mx, my, 22, 0.18, (255, 230, 120), 2))
        for _ in range(18):
            spread = random.uniform(-0.45, 0.45)
            ang = math.atan2(dy, dx) + spread
            spd = random.uniform(60, 210)
            col = random.choice([(255, 245, 160), (255, 190, 70), (255, 130, 40)])
            self.particles.append(
                Particle(mx, my, math.cos(ang) * spd, math.sin(ang) * spd,
                         random.uniform(0.12, 0.28), random.uniform(2.5, 5.0), col)
            )
        for _ in range(6):
            ang = math.atan2(dy, dx) + random.uniform(-0.6, 0.6)
            spd = random.uniform(20, 60)
            self.particles.append(
                Particle(mx, my, math.cos(ang) * spd, math.sin(ang) * spd,
                         random.uniform(0.25, 0.55), random.uniform(4.0, 7.0), (145, 150, 158), fade_smoke=True)
            )

    def _spawn_explosion(self, pos: Tuple[int, int], big: bool = False):
        cx, cy = self._board_px(pos[0], pos[1])
        self.craters.append((pos[0], pos[1], 14 if big else 9))
        if len(self.craters) > 45:
            self.craters.pop(0)
        self.shockwaves.append(
            Shockwave(cx, cy, 48 if big else 30, 0.35 if big else 0.25, (255, 175, 65), 3)
        )
        self.screen_shake = max(self.screen_shake, 8.0 if big else 4.5)

        count = 40 if big else 22
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(35, 230 if big else 155)
            col = random.choice([
                (255, 245, 150), (255, 180, 50), (245, 95, 35), (190, 50, 30)
            ])
            self.particles.append(
                Particle(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                         random.uniform(0.22, 0.6), random.uniform(2.0, 5.5), col)
            )

    @staticmethod
    def _snapshot(s):
        snap = {("t", i): (t.pos, t.hp, t.facing) for i, t in enumerate(s.tanks)}
        snap.update({("b", i): (b.pos, b.hp) for i, b in enumerate(s.bases)})
        snap.update({("w", p): (p, hp) for p, hp in s.walls.items()})
        snap["bullets"] = [(b.pos, b.direction, b.owner) for b in s.bullets]
        snap["to_move"] = s.to_move
        snap["cycle"] = s.cycle
        return snap

    def _record_hits(self, before, after_state):
        mover = before["to_move"]
        slot = self.ctrl.slots[mover]
        act = slot.last_action

        old_pos, old_hp, _ = before[("t", mover)]
        new_t = after_state.tanks[mover]
        if new_t.pos != old_pos:
            cx, cy = self._board_px(old_pos[0], old_pos[1])
            self.tread_marks.append((cx, cy, DIR_ANGLE[new_t.facing], 150))
            if len(self.tread_marks) > 90:
                self.tread_marks.pop(0)

        if act == Action.FIRE:
            self.recoil[mover] = 1.0
            self._spawn_muzzle_flash(mover, old_pos, new_t.facing)
            self.combat_log.append((f"C{after_state.cycle:02d} P{mover + 1} khai hỏa đại pháo!", P_LIGHT[mover]))

        if after_state.cycle > before["cycle"]:
            after_bullets = {(b.owner, b.direction): b.pos for b in after_state.bullets}
            for b_pos, b_dir, b_owner in before["bullets"]:
                start_px = self._board_px(b_pos[0], b_pos[1])
                if (b_owner, b_dir) in after_bullets:
                    end_pos = after_bullets[(b_owner, b_dir)]
                    end_px = self._board_px(end_pos[0], end_pos[1])
                    self.tracers.append(TracerStreak(start_px[0], start_px[1], end_px[0], end_px[1], P_LIGHT[b_owner]))

        after = self._snapshot(after_state)
        for key, val in before.items():
            if not isinstance(key, tuple):
                continue
            pos, hp = val[0], val[1]
            now_hp = after[key][1] if key in after else 0
            if now_hp < hp:
                self.flashes[pos] = 12
                destroyed = (now_hp <= 0)
                self._spawn_explosion(pos, big=(key[0] in ("t", "b") or destroyed))
                if key[0] == "t":
                    self.combat_log.append(
                        (f"C{after_state.cycle:02d} Xe tăng P{key[1] + 1} trúng đạn! (HP: {max(0, now_hp)})", DANGER)
                    )
                elif key[0] == "b":
                    self.combat_log.append(
                        (f"C{after_state.cycle:02d} Căn cứ HQ P{key[1] + 1} bị pháo kích! (HP: {max(0, now_hp)})", AMBER)
                    )
        if len(self.combat_log) > 6:
            self.combat_log = self.combat_log[-6:]

    def _act(self, fn):
        before = self._snapshot(self.ctrl.state)
        applied = fn()
        if applied:
            self._record_hits(before, self.ctrl.state)
        return applied

    # ---- events / update
    def _trigger_command(self, cmd: str):
        if cmd == "quit":
            return "quit"
        if cmd == "menu":
            return "menu"
        if cmd == "rematch":
            self.new_game()
        elif cmd == "pause":
            self.paused = not self.paused
        elif cmd == "step":
            self.paused, self.step_once = True, True
        elif cmd == "faster":
            self.delay = max(0.0, round(self.delay - 0.05, 2))
        elif cmd == "slower":
            self.delay = min(2.0, round(self.delay + 0.05, 2))
        return None

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hover_btn = None
            for rect, cmd in self.hud_buttons:
                if rect.collidepoint(mx, my):
                    self.hover_btn = cmd
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for rect, cmd in self.hud_buttons:
                if rect.collidepoint(mx, my):
                    return self._trigger_command(cmd)
        elif event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                return "quit"
            if k == pygame.K_m:
                return "menu"
            if k == pygame.K_r:
                self.new_game()
            elif k == pygame.K_p:
                self.paused = not self.paused
            elif k == pygame.K_n:
                self.paused, self.step_once = True, True
            elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.delay = max(0.0, round(self.delay - 0.05, 2))
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.delay = min(2.0, round(self.delay + 0.05, 2))
            elif k in HUMAN_KEYS and self.ctrl.needs_human():
                if self._act(lambda: self.ctrl.submit_human_action(HUMAN_KEYS[k])):
                    self.last_apply = pygame.time.get_ticks() / 1000.0
        return None

    def update(self):
        now = pygame.time.get_ticks() / 1000.0
        dt = min(0.1, max(0.001, now - self.last_frame_time))
        self.last_frame_time = now

        for p in list(self.flashes):
            self.flashes[p] -= 1
            if self.flashes[p] <= 0:
                del self.flashes[p]

        can_apply = (now - self.last_apply >= self.delay) and (not self.paused or self.step_once)
        if self._act(lambda: self.ctrl.update(can_apply)):
            self.last_apply = now
            self.step_once = False

        speed_factor = min(1.0, dt * 14.0)
        for i, t in enumerate(self.ctrl.state.tanks):
            tx, ty = float(t.pos[0]), float(t.pos[1])
            dist = math.hypot(tx - self.vis_pos[i][0], ty - self.vis_pos[i][1])
            if dist > 0.01:
                self.tread_phase[i] += dist * 18.0
            self.vis_pos[i][0] = lerp(self.vis_pos[i][0], tx, speed_factor)
            self.vis_pos[i][1] = lerp(self.vis_pos[i][1], ty, speed_factor)
            target_ang = DIR_ANGLE[t.facing]
            self.vis_angle[i] = lerp_angle(self.vis_angle[i], target_ang, min(1.0, dt * 16.0))
            self.recoil[i] = max(0.0, self.recoil[i] - dt * 4.5)

        self.screen_shake = max(0.0, self.screen_shake - dt * 28.0)
        self.particles = [p for p in self.particles if p.update(dt)]
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]
        self.tracers = [tr for tr in self.tracers if tr.update(dt)]

    # ---- drawing
    def _segmented_bar(self, screen, x, y, w, h, value, maxv, color):
        pygame.draw.rect(screen, (14, 18, 24), (x - 1, y - 1, w + 2, h + 2), border_radius=3)
        seg_w = (w - (maxv - 1) * 2) / maxv
        for idx in range(maxv):
            sx = int(x + idx * (seg_w + 2))
            sw = max(2, int(seg_w))
            c = color if idx < value else (36, 42, 52)
            pygame.draw.rect(screen, c, (sx, y, sw, h), border_radius=2)

    def draw(self, screen: pygame.Surface):
        f, s = self.fonts, self.ctrl.state
        self.hud_buttons.clear()
        screen.fill(BG)

        sh_x = int(random.uniform(-self.screen_shake, self.screen_shake)) if self.screen_shake > 0.2 else 0
        sh_y = int(random.uniform(-self.screen_shake, self.screen_shake)) if self.screen_shake > 0.2 else 0

        board_w = self.cfg.width * CELL
        board_h = self.cfg.height * CELL
        bx0 = BOARD_PAD + sh_x
        by0 = BOARD_PAD + sh_y

        # 1. Outer Metallic Battlefield Bezel & Tactical Coordinate Grid Labels (A-M, 1-13)
        pygame.draw.rect(
            screen, (25, 30, 38),
            (bx0 - 22, by0 - 22, board_w + 44, board_h + 44), border_radius=8
        )
        pygame.draw.rect(
            screen, BORDER_STEEL,
            (bx0 - 22, by0 - 22, board_w + 44, board_h + 44), 2, border_radius=8
        )
        for gx in range(self.cfg.width):
            col_lbl = chr(ord("A") + gx)
            f.draw(screen, col_lbl, (bx0 + gx * CELL + CELL // 2, by0 - 11), f.tiny_bold, MUTED, center=True)
            f.draw(screen, col_lbl, (bx0 + gx * CELL + CELL // 2, by0 + board_h + 11), f.tiny_bold, MUTED, center=True)
        for gy in range(self.cfg.height):
            row_lbl = str(gy + 1)
            f.draw(screen, row_lbl, (bx0 - 11, by0 + gy * CELL + CELL // 2), f.tiny_bold, MUTED, center=True)

        # 2. Pre-rendered Realistic Battlefield Terrain
        screen.blit(self.assets.terrain_surf, (bx0, by0))

        # 3. Persistent Scorch Craters & Tank Tread Marks (on open terrain)
        for cgx, cgy, crad in self.craters:
            if (cgx, cgy) in s.walls:
                continue
            ccx = bx0 + cgx * CELL + CELL // 2
            ccy = by0 + cgy * CELL + CELL // 2
            pygame.draw.circle(screen, (26, 25, 22), (ccx, ccy), crad)
            pygame.draw.circle(screen, (18, 17, 15), (ccx, ccy), max(3, crad - 4))

        for tcx, tcy, tang, _ in self.tread_marks:
            rad = math.radians(tang)
            perp_x = -math.sin(rad) * 11
            perp_y = math.cos(rad) * 11
            dx = math.cos(rad) * 10
            dy = math.sin(rad) * 10
            for sign in (-1, 1):
                px = int(tcx + sh_x + sign * perp_x)
                py = int(tcy + sh_y + sign * perp_y)
                pygame.draw.line(
                    screen, (34, 38, 30),
                    (px - int(dx), py - int(dy)), (px + int(dx), py + int(dy)), 3
                )

        # 4. Destructible Brick & Concrete Walls
        for pos, hp in s.walls.items():
            rx = bx0 + pos[0] * CELL
            ry = by0 + pos[1] * CELL
            wall_surf = self.assets.wall_surfs.get(hp, self.assets.wall_surfs[1])
            screen.blit(wall_surf, (rx, ry))
            badge_col = (180, 215, 140) if hp == 3 else AMBER if hp == 2 else DANGER
            pygame.draw.circle(screen, (16, 18, 22), (rx + CELL - 11, ry + CELL - 11), 7)
            f.draw(screen, str(hp), (rx + CELL - 11, ry + CELL - 11), f.tiny_bold, badge_col, shadow=False, center=True)

        # 5. Fortified Military Headquarters Bases
        for i, b in enumerate(s.bases):
            r = (bx0 + b.pos[0] * CELL, by0 + b.pos[1] * CELL, CELL, CELL)
            draw_realistic_base(screen, r, i, b.hp, f)

        # 6. Tracer Streaks
        for tr in self.tracers:
            pygame.draw.line(
                screen, tr.color,
                (int(tr.x0 + sh_x), int(tr.y0 + sh_y)),
                (int(tr.x1 + sh_x), int(tr.y1 + sh_y)), 2
            )

        # 7. Armored Tanks (with smooth position & turret rotation)
        for i, t in enumerate(s.tanks):
            if t.hp <= 0:
                wcx = bx0 + t.pos[0] * CELL + CELL // 2
                wcy = by0 + t.pos[1] * CELL + CELL // 2
                pygame.draw.circle(screen, (22, 22, 24), (wcx, wcy), 20)
                pygame.draw.rect(screen, (40, 38, 36), (wcx - 14, wcy - 12, 28, 24), border_radius=4)
                continue
            vcx = bx0 + self.vis_pos[i][0] * CELL + CELL / 2.0
            vcy = by0 + self.vis_pos[i][1] * CELL + CELL / 2.0
            is_turn = (not self.ctrl.over) and (s.to_move == i)
            draw_realistic_tank(
                screen, vcx, vcy, self.vis_angle[i], i, t.hp,
                recoil=self.recoil[i], scale=1.0, is_active=is_turn,
                treads_phase=self.tread_phase[i], show_hp=True
            )

        # 8. Armor-Piercing Shells (Bullets in Flight)
        for b in s.bullets:
            cx = bx0 + b.pos[0] * CELL + CELL // 2
            cy = by0 + b.pos[1] * CELL + CELL // 2
            dx, dy = b.direction.value
            pygame.draw.line(
                screen, P_COLORS[b.owner],
                (cx - dx * 16, cy - dy * 16), (cx, cy), 5
            )
            pygame.draw.line(
                screen, (255, 220, 90),
                (cx - dx * 10, cy - dy * 10), (cx + dx * 4, cy + dy * 4), 3
            )
            pygame.draw.circle(screen, (255, 250, 210), (cx + dx * 3, cy + dy * 3), 4)
            pygame.draw.circle(screen, P_COLORS[b.owner], (cx, cy), 7, 2)

        # 9. Shockwaves, Particles, and Hit Flashes
        for sw in self.shockwaves:
            pygame.draw.circle(
                screen, sw.color,
                (int(sw.x + sh_x), int(sw.y + sh_y)),
                int(sw.radius), sw.width
            )
        for pt in self.particles:
            ratio = max(0.0, pt.life / pt.max_life)
            rad = max(1, int(pt.size * (ratio if not pt.fade_smoke else (1.2 - 0.4 * ratio))))
            pygame.draw.circle(screen, pt.color, (int(pt.x + sh_x), int(pt.y + sh_y)), rad)

        for pos in self.flashes:
            rx = bx0 + pos[0] * CELL
            ry = by0 + pos[1] * CELL
            pygame.draw.rect(screen, (255, 165, 45), (rx + 1, ry + 1, CELL - 2, CELL - 2), 3, border_radius=4)

        # 10. Tactical Command Sidebar & Game Over Overlay
        self._draw_panel(screen)
        if self.ctrl.over:
            self._draw_game_over(screen)

    def _draw_panel(self, screen: pygame.Surface):
        f, c = self.fonts, self.ctrl
        w_win, h_win = screen.get_size()
        px0 = self.cfg.width * CELL + BOARD_PAD * 2
        pw = w_win - px0

        pygame.draw.rect(screen, PANEL_BG, (px0, 0, pw, h_win))
        pygame.draw.line(screen, BORDER_STEEL, (px0, 0), (px0, h_win), 3)

        x0 = px0 + 18
        inner_w = pw - 36

        # 1. Top Telemetry Status Header
        header_rect = pygame.Rect(x0, 14, inner_w, 64)
        pygame.draw.rect(screen, CARD_BG, header_rect, border_radius=8)
        pygame.draw.rect(screen, BORDER_STEEL, header_rect, 1, border_radius=8)

        f.draw(screen, f"CYCLE  {c.state.cycle:03d} / {MAX_CYCLES}", (x0 + 14, 20), f.sub, TEXT)

        if c.over:
            st_txt, st_col = "COMBAT ENDED", DANGER
        elif self.paused:
            st_txt, st_col = "PAUSED", AMBER
        else:
            st_txt, st_col = "LIVE COMBAT", EMERALD

        pygame.draw.circle(screen, st_col, (x0 + inner_w - 118, 31), 5)
        f.draw(screen, st_txt, (x0 + inner_w - 106, 23), f.small_bold, st_col)
        f.draw(screen, f"Tốc độ trễ: {self.delay:.2f}s / bước", (x0 + 14, 50), f.tiny, MUTED)

        prog_w = 130
        prog_x = x0 + inner_w - prog_w - 14
        pygame.draw.rect(screen, (15, 18, 24), (prog_x, 54, prog_w, 8), border_radius=4)
        fill_p = int(prog_w * min(1.0, c.state.cycle / MAX_CYCLES))
        if fill_p > 0:
            pygame.draw.rect(screen, P_LIGHT[0], (prog_x, 54, fill_p, 8), border_radius=4)

        # 2. Dual Player Tactical Telemetry Cards
        for i, slot in enumerate(c.slots):
            cy0 = 90 + i * 214
            card_h = 202
            turn = (not c.over) and (c.state.to_move == i)
            card_rect = pygame.Rect(x0, cy0, inner_w, card_h)

            pygame.draw.rect(screen, CARD_ACTIVE if turn else CARD_BG, card_rect, border_radius=8)
            pygame.draw.rect(
                screen, P_COLORS[i] if turn else (50, 58, 72),
                card_rect, 2 if turn else 1, border_radius=8
            )
            pygame.draw.rect(screen, P_COLORS[i], (x0, cy0, 6, card_h), border_radius=3)

            f.draw(screen, P_CALLSIGNS[i], (x0 + 16, cy0 + 10), f.normal, P_LIGHT[i])
            if turn:
                badge_txt = "ĐANG TÍNH TOÁN..." if not slot.is_human else "LƯỢT CỦA BẠN!"
                badge_col = AMBER if not slot.is_human else EMERALD
                f.draw(screen, badge_txt, (x0 + inner_w - 12, cy0 + 12), f.tiny_bold, badge_col, right=True)

            f.draw(screen, short(slot.name, 34), (x0 + 16, cy0 + 32), f.small_bold, TEXT)

            t, b = c.state.tanks[i], c.state.bases[i]
            f.draw(screen, f"GIÁP XE TĂNG ({max(t.hp, 0)}/{TANK_HP})", (x0 + 16, cy0 + 58), f.tiny_bold, MUTED)
            self._segmented_bar(
                screen, x0 + 165, cy0 + 60, inner_w - 180, 11,
                max(t.hp, 0), TANK_HP, EMERALD if t.hp >= 3 else DANGER
            )

            f.draw(screen, f"CĂN CỨ HQ ({max(b.hp, 0)}/{BASE_HP})", (x0 + 16, cy0 + 82), f.tiny_bold, MUTED)
            self._segmented_bar(
                screen, x0 + 165, cy0 + 84, inner_w - 180, 11,
                max(b.hp, 0), BASE_HP, AMBER if b.hp >= 4 else DANGER
            )

            last = slot.last_action.name if slot.last_action else "READY"
            ammo_ready = not c.state.has_bullet_in_flight(i)
            f.draw(screen, f"Lệnh cuối: {last}", (x0 + 16, cy0 + 108), f.small_bold, P_LIGHT[i])
            f.draw(
                screen,
                "ĐẠN PHÁO: SẴN SÀNG" if ammo_ready else "ĐẠN PHÁO: ĐANG BAY",
                (x0 + inner_w - 14, cy0 + 110), f.tiny_bold,
                EMERALD if ammo_ready else AMBER, right=True
            )

            if not slot.is_human:
                st = slot.stats
                f.draw(
                    screen,
                    f"Tốc độ duyệt: {slot.last_think * 1000:.1f} ms  (TB: {st.avg_time * 1000:.1f} ms | Max: {st.max_time * 1000:.0f} ms)",
                    (x0 + 16, cy0 + 134), f.tiny, MUTED
                )
                load_w = inner_w - 32
                pygame.draw.rect(screen, (16, 20, 26), (x0 + 16, cy0 + 154, load_w, 6), border_radius=3)
                ratio = min(1.0, slot.last_think / 1.0)
                if ratio > 0:
                    pygame.draw.rect(
                        screen, P_COLORS[i] if ratio < 0.8 else DANGER,
                        (x0 + 16, cy0 + 154, int(load_w * ratio), 6), border_radius=3
                    )
                err_any = (st.timeouts or st.errors or st.invalid)
                f.draw(
                    screen,
                    f"Moves: {st.moves}   Timeouts: {st.timeouts}   Errors: {st.errors}   Invalid: {st.invalid}",
                    (x0 + 16, cy0 + 168), f.tiny,
                    DANGER if err_any else MUTED
                )
            else:
                f.draw(
                    screen,
                    "Phím: [WASD / Mũi tên] Di chuyển  |  [SPACE] Bắn  |  [X] Chờ",
                    (x0 + 16, cy0 + 142), f.tiny_bold, EMERALD
                )

        # 3. Live Combat Log Box
        log_y = 518
        log_h = 132
        log_rect = pygame.Rect(x0, log_y, inner_w, log_h)
        pygame.draw.rect(screen, (16, 20, 26), log_rect, border_radius=8)
        pygame.draw.rect(screen, BORDER_STEEL, log_rect, 1, border_radius=8)
        f.draw(screen, "NHẬT KÝ CHIẾN TRƯỜNG (COMBAT LOG)", (x0 + 12, log_y + 8), f.tiny_bold, AMBER)
        for idx, (msg, col) in enumerate(self.combat_log[-5:]):
            f.draw(screen, short(msg, 48), (x0 + 12, log_y + 28 + idx * 19), f.tiny, col)

        # 4. Interactive Tactical Control Buttons Bar
        btn_y = h_win - 122
        btns = [
            ("TIẾP TỤC [P]" if self.paused else "TẠM DỪNG [P]", "pause"),
            ("BƯỚC TIẾP [N]", "step"),
            ("- GIẢM TỐC", "slower"),
            ("+ TĂNG TỐC", "faster"),
            ("ĐẤU LẠI [R]", "rematch"),
            ("VỀ MENU [M]", "menu"),
        ]
        cols = 2
        bw = (inner_w - 10) // cols
        bh = 32
        for idx, (lbl, cmd) in enumerate(btns):
            c_idx = idx % cols
            r_idx = idx // cols
            bx = x0 + c_idx * (bw + 10)
            by = btn_y + r_idx * (bh + 6)
            brect = pygame.Rect(bx, by, bw, bh)
            hov = (self.hover_btn == cmd)
            pygame.draw.rect(screen, (45, 56, 74) if hov else (30, 37, 48), brect, border_radius=6)
            pygame.draw.rect(screen, AMBER if hov else BORDER_STEEL, brect, 1, border_radius=6)
            f.draw(screen, lbl, brect.center, f.tiny_bold, TEXT, center=True)
            self.hud_buttons.append((brect, cmd))

    def _draw_game_over(self, screen: pygame.Surface):
        f, r = self.fonts, self.ctrl.result()
        u = self.ctrl.state.utility()
        board_w = self.cfg.width * CELL + BOARD_PAD * 2
        board_h = self.cfg.height * CELL + BOARD_PAD * 2

        overlay = pygame.Surface((board_w, board_h), pygame.SRCALPHA)
        overlay.fill((8, 10, 15, 175))
        screen.blit(overlay, (0, 0))

        text = "TRẬN ĐẤU HÒA (DRAW)" if r == 0 else f"{P_CALLSIGNS[0 if r > 0 else 1]} CHIẾN THẮNG!"
        color = AMBER if r == 0 else P_LIGHT[0 if r > 0 else 1]
        border_c = AMBER if r == 0 else P_COLORS[0 if r > 0 else 1]

        mw, mh = 460, 210
        mx = board_w // 2 - mw // 2
        my = board_h // 2 - mh // 2

        pygame.draw.rect(screen, (18, 22, 30), (mx, my, mw, mh), border_radius=12)
        pygame.draw.rect(screen, border_c, (mx, my, mw, mh), 3, border_radius=12)

        f.draw(screen, "KẾT QUẢ CHIẾN DỊCH", (board_w // 2, my + 28), f.small_bold, MUTED, center=True)
        f.draw(screen, text, (board_w // 2, my + 68), f.big, color, center=True)
        f.draw(
            screen,
            f"Chu kỳ kết thúc: {self.ctrl.state.cycle}   |   Điểm Utility (MAX): {u:+d}",
            (board_w // 2, my + 112), f.small_bold, TEXT, center=True
        )

        rem_rect = pygame.Rect(mx + 45, my + 144, 175, 42)
        menu_rect = pygame.Rect(mx + mw - 220, my + 144, 175, 42)
        for rect, lbl, cmd, col in [
            (rem_rect, "ĐẤU LẠI [R]", "rematch", (40, 130, 75)),
            (menu_rect, "VỀ MENU [M]", "menu", (48, 60, 82)),
        ]:
            pygame.draw.rect(screen, col, rect, border_radius=7)
            pygame.draw.rect(screen, TEXT, rect, 1, border_radius=7)
            f.draw(screen, lbl, rect.center, f.small_bold, TEXT, center=True)
            self.hud_buttons.append((rect, cmd))


# ------------------------------------------------------------------------------ main
def resolve_spec(token, specs):
    if os.path.isfile(token):
        return file_spec(token)
    token = token.lower()
    for s in specs:
        if token in s.label.lower():
            return s
    raise SystemExit(f"Unknown player '{token}'. Options: " + "; ".join(s.label for s in specs))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--p1", help="player 1: label substring or plugin path (skips the menu)")
    ap.add_argument("--p2", help="player 2: label substring or plugin path")
    args = ap.parse_args(argv)

    pygame.init()
    cfg = GameConfig()
    size = (
        max(cfg.width * CELL + BOARD_PAD * 2 + PANEL_W, 1220),
        max(cfg.height * CELL + BOARD_PAD * 2, 792)
    )
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("Tank Battle - Tactical Command & Adversarial Search")
    clock = pygame.time.Clock()
    fonts = Fonts()
    specs = all_specs()

    menu = MenuScreen(specs, fonts)
    game = None
    if args.p1 and args.p2:
        game = GameScreen(resolve_spec(args.p1, specs), resolve_spec(args.p2, specs), fonts)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if game is None:
                out = menu.handle(event)
                if out == "quit":
                    running = False
                elif out and out[0] == "start":
                    game = GameScreen(out[1], out[2], fonts)
            else:
                out = game.handle(event)
                if out == "quit":
                    running = False
                elif out == "menu":
                    game = None
        if game is None:
            menu.draw(screen)
        else:
            game.update()
            game.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
