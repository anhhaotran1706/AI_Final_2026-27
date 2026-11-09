"""Task 3 - Requirement 3: PyGame UI for the Kakuro CSP Solver.

Upgraded Interactive CSP Laboratory & Tactile Kakuro Studio:
  * Realistic 3D-beveled Kakuro board with split diagonal clue tiles, live run-sum verification,
    ivory variable tiles, 3x3 candidate pencil-mark badges, and eliminated-digit highlights.
  * Step-by-step & reversible visualization of:
      - Variable DOMAINS (candidates 1..9 + pruned digits in the current step),
      - CONSTRAINT PROPAGATION (focused run beam, narrowed cells, domain wipeout conflicts),
      - BACKTRACKING SEARCH (search decision badges, depth indicator, backtrack undo trace).
  * Interactive Mouse + Keyboard controls:
      - Click or drag the Timeline Scrubber (with color-coded event markers),
      - Hover or click any cell on the board to inspect its Across/Down runs and valid combinations,
      - Switch Solver Presets (1/2/3), switch or generate puzzles, or open the Puzzle Selector Hub [M].

Run:   python kakuro_gui.py [puzzle.txt]          (default puzzles/complex_9x9.txt)
Keys:  SPACE play/pause   RIGHT/LEFT step forward/back   UP/DOWN speed
       R restart   E jump to end   C next conflict   B next backtrack
       1/2/3 solver preset (full / propagation only / plain backtracking)
       M puzzle & mode selector menu   G generate random puzzle   L load file
       drag & drop a puzzle .txt file onto the window to load it     ESC quit
"""
import math
import os
import random
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

import pygame

from kakuro_csp import CLUE_RE, Cell, KakuroCSP, KakuroPuzzle, Run
from kakuro_trace import PRESETS, TraceStep, build_trace

try:
    from generate_puzzle import generate as generate_demo_puzzle, random_pattern
    HAS_GENERATOR = True
except Exception:
    HAS_GENERATOR = False

# --------------------------------------------------------------------------- layout & palette
BOARD_AREA_W = 740
BOARD_AREA_H = 780
PANEL_W = 500
WIN_W = BOARD_AREA_W + PANEL_W
WIN_H = 820

BG = (15, 18, 24)
BOARD_FRAME = (26, 31, 40)
PANEL_BG = (20, 24, 32)
CARD_BG = (27, 33, 44)
CARD_ALT = (33, 40, 54)
BORDER_STEEL = (60, 72, 92)

TEXT = (238, 242, 248)
MUTED = (148, 160, 178)
DARK_SLATE = (34, 39, 48)
OBSIDIAN = (22, 26, 33)

# Tile colors (realistic ivory/porcelain white cells & crisp ink colors)
TILE_IVORY = (246, 244, 238)
TILE_DECIDED = (214, 232, 255)
TILE_PROPAGATED = (214, 245, 224)
TILE_CONFLICT = (255, 208, 208)
TILE_CHANGED = (255, 238, 205)

INK_DECIDED = (22, 82, 195)
INK_PROPAGATED = (18, 125, 62)
INK_CANDIDATE = (68, 76, 92)
INK_PRUNED = (215, 55, 55)

KIND_COLORS = {
    "init": (140, 155, 175),
    "assign": (68, 148, 255),
    "revise": (245, 178, 55),
    "conflict": (242, 82, 75),
    "backtrack": (198, 118, 242),
    "solution": (72, 215, 128),
}

KIND_LABELS_VI = {
    "init": "KHỞI TẠO MIỀN GIÁ TRỊ",
    "assign": "GÁN BIẾN (SEARCH DECISION)",
    "revise": "LAN TRUYỀN RÀNG BUỘC",
    "conflict": "XUNG ĐỘT (DOMAIN RỖNG)",
    "backtrack": "QUAY LUI (BACKTRACK)",
    "solution": "TÌM THẤY NGHIỆM HỢP LỆ",
}

PRESET_SHORT = [
    "1. Full (Prop + MRV + Deg + LCV)",
    "2. Propagation (Thứ tự tĩnh)",
    "3. Backtracking thuần túy",
]

SPEEDS = [1, 2, 5, 10, 20, 50, 100]  # steps per second


def _load_unicode_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Loads a system font supporting full Vietnamese Unicode characters."""
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


def wrap(text: str, width: int) -> List[str]:
    lines, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


def short(text: str, n: int = 38) -> str:
    return text if len(text) <= n else text[: n - 1] + "..."


class KakuroApp:
    def __init__(self, text: str, label: str):
        self.here = os.path.dirname(os.path.abspath(__file__))
        self.puzzles_dir = os.path.join(self.here, "puzzles")
        self.preset_idx = 0
        self.speed_idx = 3
        self.message = "Mẹo: Di chuột lên ô bất kỳ để soi miền giá trị & tổ hợp tổng; Click thanh tiến độ để tua nhanh."
        self.msg_color = (140, 205, 255)
        self.show_menu = False
        self.dragging_timeline = False
        self.hover_cell: Optional[Cell] = None
        self.selected_cell: Optional[Cell] = None
        self.ui_buttons: List[Tuple[pygame.Rect, str, object]] = []
        self.hover_btn: Optional[Tuple[str, object]] = None
        self.timeline_rect = pygame.Rect(0, 0, 10, 10)
        self.gen_seed = 10

        self._init_ui_fonts()
        self.available_puzzles = self._discover_puzzles()
        self.set_puzzle(text, label)

    def _init_ui_fonts(self):
        pygame.font.init()
        self.f_tiny = _load_unicode_font(11, bold=False)
        self.f_tiny_b = _load_unicode_font(11, bold=True)
        self.f_small = _load_unicode_font(13, bold=False)
        self.f_small_b = _load_unicode_font(13, bold=True)
        self.f_text = _load_unicode_font(15, bold=False)
        self.f_text_b = _load_unicode_font(15, bold=True)
        self.f_sub = _load_unicode_font(18, bold=True)
        self.f_title = _load_unicode_font(24, bold=True)
        self.f_big = _load_unicode_font(30, bold=True)

    def _discover_puzzles(self) -> List[Tuple[str, str]]:
        """Returns list of (filename, full_path) in puzzles/."""
        out = []
        if os.path.isdir(self.puzzles_dir):
            for fn in sorted(os.listdir(self.puzzles_dir)):
                if fn.endswith(".txt"):
                    out.append((fn, os.path.join(self.puzzles_dir, fn)))
        return out

    # ------------------------------------------------------------------ data
    def set_puzzle(self, text: str, label: str):
        self.text, self.label = text, label
        self.selected_cell = None
        self.hover_cell = None
        self.rebuild()

    def rebuild(self):
        preset = list(PRESETS)[self.preset_idx]
        self.csp, self.steps, self.solution, self.stats, self.truncated = build_trace(
            self.text, preset
        )
        pz = self.csp.puzzle
        self.grid, self.rows, self.cols = pz.grid, pz.rows, pz.cols

        # Calculate optimal cell size & centered board offsets inside BOARD_AREA
        usable_w = BOARD_AREA_W - 88
        usable_h = WIN_H - 130
        self.cell = max(32, min(82, min(usable_w // self.cols, usable_h // self.rows)))
        self.board_w = self.cols * self.cell
        self.board_h = self.rows * self.cell
        self.board_x = (BOARD_AREA_W - self.board_w) // 2 + 8
        self.board_y = (WIN_H - self.board_h) // 2 + 18

        # Cell-scaled typography
        self.f_digit = _load_unicode_font(max(18, int(self.cell * 0.56)), bold=True)
        self.f_cand = _load_unicode_font(max(10, int(self.cell * 0.20)), bold=True)
        self.f_clue = _load_unicode_font(max(11, int(self.cell * 0.24)), bold=True)

        # Precompute clue run lookup: (clue_r, clue_c, 'across'|'down') -> Run
        self.clue_runs: Dict[Tuple[int, int, str], Run] = {}
        for r in self.csp.runs:
            self.clue_runs[(r.clue_cell[0], r.clue_cell[1], r.direction)] = r

        self.pos, self.playing, self.acc = 0, False, 0.0
        self.last_ticks = pygame.time.get_ticks()

    @property
    def size(self):
        return (WIN_W, WIN_H)

    @property
    def step(self) -> TraceStep:
        return self.steps[self.pos]

    def _prev_domains(self) -> Optional[Dict[Cell, frozenset]]:
        if self.pos > 0:
            return self.steps[self.pos - 1].domains
        return None

    # ---------------------------------------------------------------- actions
    def jump_next(self, kind: str):
        for i in range(self.pos + 1, len(self.steps)):
            if self.steps[i].kind == kind:
                self.pos, self.playing = i, False
                self.message = f"Đã nhảy tới bước {i + 1}: {KIND_LABELS_VI.get(kind, kind)}"
                self.msg_color = KIND_COLORS.get(kind, TEXT)
                return
        self.message = f"Không còn bước '{kind}' nào phía sau bước hiện tại."
        self.msg_color = (245, 190, 75)

    def jump_prev(self, kind: str):
        for i in range(self.pos - 1, -1, -1):
            if self.steps[i].kind == kind:
                self.pos, self.playing = i, False
                return
        self.message = f"Không có bước '{kind}' nào phía trước."
        self.msg_color = (245, 190, 75)

    def generate_new_puzzle(self, dims: Tuple[int, int] = (7, 7)):
        if not HAS_GENERATOR:
            self.message = "Không tìm thấy module generate_puzzle.py"
            self.msg_color = KIND_COLORS["conflict"]
            return
        for _ in range(15):
            self.gen_seed += 1
            try:
                pat = random_pattern(dims[0], dims[1], p=0.24, seed=self.gen_seed)
                txt, _ = generate_demo_puzzle(pat, seed=self.gen_seed)
                self.set_puzzle(txt, f"Random_{dims[0]}x{dims[1]}_s{self.gen_seed}.txt")
                self.show_menu = False
                self.message = f"Đã sinh ngẫu nhiên bàn cờ {dims[0]}x{dims[1]} (seed={self.gen_seed})."
                self.msg_color = KIND_COLORS["solution"]
                return
            except Exception:
                continue
        self.message = "Không thể sinh bàn cờ mới, hãy thử lại."
        self.msg_color = KIND_COLORS["conflict"]

    def open_file_dialog(self):
        try:
            import tkinter
            from tkinter import filedialog
            root = tkinter.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                initialdir=self.puzzles_dir,
                filetypes=[("Kakuro puzzle", "*.txt"), ("All files", "*.*")]
            )
            root.destroy()
        except Exception:
            self.message = "Kéo & thả trực tiếp file .txt vào cửa sổ này để nạp bàn cờ!"
            self.msg_color = KIND_COLORS["revise"]
            return
        if path and os.path.isfile(path):
            try:
                self.set_puzzle(open(path).read(), os.path.basename(path))
                self.show_menu = False
                self.message = f"Đã tải bàn cờ {os.path.basename(path)}"
                self.msg_color = KIND_COLORS["solution"]
            except Exception as e:
                self.message = f"Lỗi đọc file: {e}"
                self.msg_color = KIND_COLORS["conflict"]

    def _scrub_to_mouse(self, mx: int):
        if self.timeline_rect.width <= 1 or len(self.steps) <= 1:
            return
        ratio = max(0.0, min(1.0, (mx - self.timeline_rect.left) / self.timeline_rect.width))
        self.pos = int(round(ratio * (len(self.steps) - 1)))
        self.playing = False

    def _exec_button(self, act: str, payload: object):
        if act == "toggle_menu":
            self.show_menu = not self.show_menu
        elif act == "close_menu":
            self.show_menu = False
        elif act == "preset":
            self.preset_idx = int(payload)
            self.rebuild()
            self.message = f"Đã chuyển cấu hình: {PRESET_SHORT[self.preset_idx]}"
            self.msg_color = KIND_COLORS["assign"]
        elif act == "load_puzzle":
            fn, full_path = payload
            try:
                self.set_puzzle(open(full_path).read(), fn)
                self.show_menu = False
                self.message = f"Đã mở bàn cờ: {fn}"
                self.msg_color = KIND_COLORS["solution"]
            except Exception as e:
                self.message = f"Lỗi nạp {fn}: {e}"
                self.msg_color = KIND_COLORS["conflict"]
        elif act == "gen_puzzle":
            self.generate_new_puzzle(payload)
        elif act == "open_file":
            self.open_file_dialog()
        elif act == "play_pause":
            if self.pos >= len(self.steps) - 1:
                self.pos = 0
            self.playing = not self.playing
        elif act == "step_fwd":
            self.pos, self.playing = min(self.pos + 1, len(self.steps) - 1), False
        elif act == "step_back":
            self.pos, self.playing = max(self.pos - 1, 0), False
        elif act == "restart":
            self.pos, self.playing = 0, False
        elif act == "jump_end":
            self.pos, self.playing = len(self.steps) - 1, False
        elif act == "next_conflict":
            self.jump_next("conflict")
        elif act == "next_backtrack":
            self.jump_next("backtrack")
        elif act == "speed_up":
            self.speed_idx = min(self.speed_idx + 1, len(SPEEDS) - 1)
        elif act == "speed_down":
            self.speed_idx = max(self.speed_idx - 1, 0)

    # ---------------------------------------------------------------- events
    def handle(self, event):
        if event.type == pygame.DROPFILE:
            try:
                self.set_puzzle(open(event.file).read(), os.path.basename(event.file))
                self.show_menu = False
                self.message = f"Đã tải file {os.path.basename(event.file)}"
                self.msg_color = KIND_COLORS["solution"]
            except Exception as e:
                self.message = f"Không thể đọc file: {e}"
                self.msg_color = KIND_COLORS["conflict"]
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_timeline = False

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.dragging_timeline and not self.show_menu:
                self._scrub_to_mouse(mx)
                return None

            self.hover_btn = None
            for rect, act, payload in self.ui_buttons:
                if rect.collidepoint(mx, my):
                    self.hover_btn = (act, payload)
                    break

            # Track hovered cell on the Kakuro board
            if not self.show_menu and (
                self.board_x <= mx < self.board_x + self.board_w
                and self.board_y <= my < self.board_y + self.board_h
            ):
                c = (mx - self.board_x) // self.cell
                r = (my - self.board_y) // self.cell
                self.hover_cell = (int(r), int(c))
            else:
                self.hover_cell = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not self.show_menu and self.timeline_rect.inflate(0, 10).collidepoint(mx, my):
                self.dragging_timeline = True
                self._scrub_to_mouse(mx)
                return None

            for rect, act, payload in self.ui_buttons:
                if rect.collidepoint(mx, my):
                    self._exec_button(act, payload)
                    return None

            # Click on board cell to lock/unlock cell inspector
            if not self.show_menu and self.hover_cell is not None:
                if self.selected_cell == self.hover_cell:
                    self.selected_cell = None
                else:
                    self.selected_cell = self.hover_cell
                return None

        if event.type != pygame.KEYDOWN:
            return None

        k = event.key
        if k == pygame.K_ESCAPE:
            if self.show_menu:
                self.show_menu = False
                return None
            return "quit"
        if k == pygame.K_m:
            self.show_menu = not self.show_menu
            return None
        if k == pygame.K_g:
            self.generate_new_puzzle((7, 7))
            return None
        if k == pygame.K_l:
            self.open_file_dialog()
            return None

        self.message = ""
        if k == pygame.K_SPACE:
            if self.pos >= len(self.steps) - 1:
                self.pos = 0
            self.playing = not self.playing
        elif k == pygame.K_RIGHT:
            self.pos, self.playing = min(self.pos + 1, len(self.steps) - 1), False
        elif k == pygame.K_LEFT:
            self.pos, self.playing = max(self.pos - 1, 0), False
        elif k == pygame.K_UP:
            self.speed_idx = min(self.speed_idx + 1, len(SPEEDS) - 1)
        elif k == pygame.K_DOWN:
            self.speed_idx = max(self.speed_idx - 1, 0)
        elif k == pygame.K_r:
            self.pos, self.playing = 0, False
        elif k == pygame.K_e:
            self.pos, self.playing = len(self.steps) - 1, False
        elif k == pygame.K_c:
            self.jump_next("conflict")
        elif k == pygame.K_b:
            self.jump_next("backtrack")
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.preset_idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[k]
            self.rebuild()
        return None

    def update(self):
        now = pygame.time.get_ticks()
        dt = (now - self.last_ticks) / 1000.0
        self.last_ticks = now
        if self.playing and not self.show_menu:
            self.acc += dt * SPEEDS[self.speed_idx]
            while self.acc >= 1 and self.pos < len(self.steps) - 1:
                self.pos += 1
                self.acc -= 1
            if self.pos >= len(self.steps) - 1:
                self.playing = False

    # ---------------------------------------------------------------- helpers for run status
    def _run_status(self, run: Optional[Run], st: TraceStep) -> str:
        """Returns 'conflict', 'focus', 'solved', or 'normal' for a clue run."""
        if run is None:
            return "normal"
        if st.focus and set(run.cells) == set(st.focus):
            return "conflict" if st.kind == "conflict" else "focus"
        # Check if all cells in run have singleton domains that sum to run.total with distinct digits
        vals = [next(iter(st.domains[c])) for c in run.cells if len(st.domains[c]) == 1]
        if len(vals) == run.length and len(set(vals)) == run.length and sum(vals) == run.total:
            return "solved"
        return "normal"

    def _inspected_cell(self) -> Optional[Cell]:
        return self.selected_cell if self.selected_cell is not None else self.hover_cell

    # ---------------------------------------------------------------- drawing
    def _text(
        self,
        screen: pygame.Surface,
        s: str,
        pos: Tuple[int, int],
        font=None,
        color=TEXT,
        center=False,
        right=False,
        shadow=False,
    ):
        f = font or self.f_text
        surf = f.render(str(s), True, color)
        x, y = pos
        if center:
            x -= surf.get_width() // 2
            y -= surf.get_height() // 2
        elif right:
            x -= surf.get_width()
        if shadow:
            sh = f.render(str(s), True, (8, 10, 14))
            screen.blit(sh, (x + 1, y + 1))
        screen.blit(surf, (x, y))
        return surf.get_rect(topleft=(x, y))

    def _draw_clue(self, screen: pygame.Surface, r: int, c: int, tok: str, st: TraceStep):
        x = self.board_x + c * self.cell
        y = self.board_y + r * self.cell
        cs = self.cell

        # Base dark obsidian tile with 3D bevel
        pygame.draw.rect(screen, OBSIDIAN, (x, y, cs, cs))
        m = CLUE_RE.match(tok)
        if not m:
            # Pure solid block '#'
            pygame.draw.rect(screen, (28, 33, 42), (x + 2, y + 2, cs - 4, cs - 4), border_radius=3)
            pygame.draw.line(screen, (40, 47, 60), (x + 3, y + 3), (x + cs - 4, y + 3), 1)
            pygame.draw.line(screen, (40, 47, 60), (x + 3, y + 3), (x + 3, y + cs - 4), 1)
            # Subtle decorative diamond in solid block center
            cx, cy = x + cs // 2, y + cs // 2
            pygame.draw.polygon(
                screen, (36, 42, 54),
                [(cx, cy - 4), (cx + 4, cy), (cx, cy + 4), (cx - 4, cy)]
            )
            pygame.draw.rect(screen, (52, 60, 74), (x, y, cs, cs), 1)
            return

        down_str, across_str = m.group(1), m.group(2)
        down_run = self.clue_runs.get((r, c, "down"))
        across_run = self.clue_runs.get((r, c, "across"))
        down_st = self._run_status(down_run, st)
        across_st = self._run_status(across_run, st)

        tri_colors = {
            "normal": (38, 44, 56),
            "focus": (82, 68, 28),
            "conflict": (98, 32, 34),
            "solved": (26, 68, 46),
        }
        txt_colors = {
            "normal": (235, 240, 248),
            "focus": (255, 220, 90),
            "conflict": (255, 130, 125),
            "solved": (110, 240, 155),
        }

        # Lower-left triangle (DOWN clue)
        pts_down = [(x, y), (x, y + cs), (x + cs, y + cs)]
        pygame.draw.polygon(
            screen,
            tri_colors[down_st] if down_str else (24, 28, 36),
            pts_down
        )

        # Upper-right triangle (ACROSS clue)
        pts_across = [(x, y), (x + cs, y), (x + cs, y + cs)]
        pygame.draw.polygon(
            screen,
            tri_colors[across_st] if across_str else (24, 28, 36),
            pts_across
        )

        # Diagonal brass/steel divider line
        pygame.draw.line(screen, (125, 138, 158), (x, y), (x + cs, y + cs), 2)
        pygame.draw.rect(screen, (62, 72, 88), (x, y, cs, cs), 1)

        if down_str:
            col = txt_colors[down_st]
            tx, ty = x + int(cs * 0.28), y + int(cs * 0.74)
            self._text(screen, down_str, (tx, ty), self.f_clue, col, center=True, shadow=True)
            # Small downward arrow indicator
            if cs >= 48:
                ax, ay = x + 6, y + cs - 8
                pygame.draw.polygon(screen, col, [(ax, ay), (ax - 3, ay - 4), (ax + 3, ay - 4)])

        if across_str:
            col = txt_colors[across_st]
            tx, ty = x + int(cs * 0.72), y + int(cs * 0.27)
            self._text(screen, across_str, (tx, ty), self.f_clue, col, center=True, shadow=True)
            if cs >= 48:
                ax, ay = x + cs - 5, y + 7
                pygame.draw.polygon(screen, col, [(ax, ay), (ax - 4, ay - 3), (ax - 4, ay + 3)])

    def _draw_white(
        self,
        screen: pygame.Surface,
        r: int,
        c: int,
        st: TraceStep,
        prev_doms: Optional[Dict[Cell, frozenset]],
        inspected_cells: Set[Cell],
    ):
        cell = (r, c)
        x = self.board_x + c * self.cell
        y = self.board_y + r * self.cell
        cs = self.cell
        dom = st.domains[cell]
        prev_dom = prev_doms.get(cell, dom) if prev_doms else dom
        pruned_now = (prev_dom - dom) if (cell in st.changed) else frozenset()

        # Choose realistic tile background & ink color
        if st.kind == "conflict" and (cell in st.focus or len(dom) == 0):
            bg, fg = TILE_CONFLICT, (195, 28, 28)
        elif cell in st.assigned:
            bg, fg = TILE_DECIDED, INK_DECIDED
        elif len(dom) == 1:
            bg, fg = TILE_PROPAGATED, INK_PROPAGATED
        elif cell in st.changed:
            bg, fg = TILE_CHANGED, INK_CANDIDATE
        else:
            bg, fg = TILE_IVORY, INK_CANDIDATE

        # Subtle tint if cell belongs to currently inspected run
        if cell in inspected_cells and bg == TILE_IVORY:
            bg = (232, 240, 252)

        # Recessed tile base + inner porcelain bevel
        pygame.draw.rect(screen, (165, 172, 182), (x, y, cs, cs))
        pygame.draw.rect(screen, bg, (x + 1, y + 1, cs - 2, cs - 2), border_radius=3)
        pygame.draw.line(screen, (255, 255, 255), (x + 2, y + 2), (x + cs - 3, y + 2), 1)
        pygame.draw.line(screen, (255, 255, 255), (x + 2, y + 2), (x + 2, y + cs - 3), 1)

        if len(dom) == 0:
            self._text(screen, "∅", (x + cs // 2, y + cs // 2), self.f_digit, (210, 35, 35), center=True)
        elif len(dom) == 1:
            val = next(iter(dom))
            self._text(screen, str(val), (x + cs // 2, y + cs // 2 + 2), self.f_digit, fg, center=True)
            # Corner badge showing whether value came from Search Decision or Constraint Propagation
            if cs >= 46:
                tag_txt = "TRY" if cell in st.assigned else "PROP"
                tag_col = (55, 120, 235) if cell in st.assigned else (40, 165, 90)
                pygame.draw.rect(screen, tag_col, (x + 3, y + 3, 26 if tag_txt == "PROP" else 22, 11), border_radius=2)
                self._text(screen, tag_txt, (x + (16 if tag_txt == "PROP" else 14), y + 8), self.f_tiny_b, (255, 255, 255), center=True)
        else:
            # 3x3 candidate mini-grid with pill badges and pruned-digit strikethrough
            pad = 3
            inner = cs - pad * 2
            third = inner / 3.0
            for d in range(1, 10):
                cx = int(x + pad + ((d - 1) % 3 + 0.5) * third)
                cy = int(y + pad + ((d - 1) // 3 + 0.5) * third)
                if d in dom:
                    if cs >= 54:
                        r_pill = int(third * 0.42)
                        pygame.draw.rect(
                            screen, (232, 230, 222),
                            (cx - r_pill, cy - r_pill, r_pill * 2, r_pill * 2),
                            border_radius=3
                        )
                    self._text(screen, str(d), (cx, cy), self.f_cand, fg, center=True)
                elif d in pruned_now:
                    # Show recently eliminated candidate in red with a strikethrough
                    self._text(screen, str(d), (cx, cy), self.f_cand, INK_PRUNED, center=True)
                    pygame.draw.line(screen, INK_PRUNED, (cx - 5, cy + 4), (cx + 5, cy - 4), 2)

        # Highlight borders for focus run, changed domain, or user selection
        if cell in st.focus:
            focus_col = (240, 175, 20) if st.kind != "conflict" else (225, 45, 45)
            pygame.draw.rect(screen, focus_col, (x + 1, y + 1, cs - 2, cs - 2), 3, border_radius=3)
        if cell in st.changed:
            ch_col = KIND_COLORS.get(st.kind, (255, 130, 25))
            pygame.draw.rect(screen, ch_col, (x + 3, y + 3, cs - 6, cs - 6), 2, border_radius=3)

        insp = self._inspected_cell()
        if insp == cell:
            pygame.draw.rect(screen, (50, 150, 255), (x + 1, y + 1, cs - 2, cs - 2), 3, border_radius=3)

    def draw(self, screen: pygame.Surface):
        st = self.step
        prev_doms = self._prev_domains()
        self.ui_buttons.clear()
        screen.fill(BG)

        # 1. Top Bar above the Board (Quick Puzzle & Mode Selector)
        self._draw_top_bar(screen)

        # 2. Board Outer Frame & Coordinate Headers
        frame_pad = 24
        fx = self.board_x - frame_pad
        fy = self.board_y - frame_pad
        fw = self.board_w + frame_pad * 2
        fh = self.board_h + frame_pad * 2

        pygame.draw.rect(screen, (10, 12, 16), (fx + 4, fy + 6, fw, fh), border_radius=10)
        pygame.draw.rect(screen, BOARD_FRAME, (fx, fy, fw, fh), border_radius=10)
        pygame.draw.rect(screen, BORDER_STEEL, (fx, fy, fw, fh), 2, border_radius=10)

        for c in range(self.cols):
            cx = self.board_x + c * self.cell + self.cell // 2
            self._text(screen, f"C{c + 1}", (cx, fy + 11), self.f_tiny_b, MUTED, center=True)
        for r in range(self.rows):
            ry = self.board_y + r * self.cell + self.cell // 2
            self._text(screen, f"R{r + 1}", (fx + 12, ry), self.f_tiny_b, MUTED, center=True)

        # Determine cells belonging to currently inspected cell's runs
        insp = self._inspected_cell()
        inspected_run_cells: Set[Cell] = set()
        if insp and insp in self.csp.runs_of:
            for r_obj in self.csp.runs_of[insp]:
                inspected_run_cells.update(r_obj.cells)

        # 3. Draw Grid Cells
        for r in range(self.rows):
            for c in range(self.cols):
                tok = self.grid[r][c]
                if tok == ".":
                    self._draw_white(screen, r, c, st, prev_doms, inspected_run_cells)
                else:
                    self._draw_clue(screen, r, c, tok, st)

        # 4. Draw Right-hand CSP Telemetry & Control Panel
        self._draw_panel(screen, st)

        # 5. Optional Puzzle & Mode Selection Modal Overlay
        if self.show_menu:
            self._draw_menu_modal(screen)

    def _draw_top_bar(self, screen: pygame.Surface):
        pygame.draw.rect(screen, PANEL_BG, (0, 0, BOARD_AREA_W, 52))
        pygame.draw.line(screen, BORDER_STEEL, (0, 52), (BOARD_AREA_W, 52), 1)

        # Menu Hub button
        m_rect = pygame.Rect(14, 10, 172, 32)
        m_hov = self.hover_btn == ("toggle_menu", None)
        pygame.draw.rect(screen, (48, 92, 165) if m_hov else (36, 68, 125), m_rect, border_radius=6)
        pygame.draw.rect(screen, (120, 185, 255), m_rect, 1, border_radius=6)
        self._text(screen, "CHỌN BÀN CỜ / CHẾ ĐỘ [M]", m_rect.center, self.f_tiny_b, TEXT, center=True)
        self.ui_buttons.append((m_rect, "toggle_menu", None))

        # Quick puzzle pills
        px = 196
        for fn, full_path in self.available_puzzles[:3]:
            short_fn = fn.replace(".txt", "")
            pw = max(88, self.f_tiny_b.size(short_fn)[0] + 22)
            p_rect = pygame.Rect(px, 10, pw, 32)
            active = (self.label == fn)
            hov = self.hover_btn == ("load_puzzle", (fn, full_path))
            bg_c = (44, 62, 88) if active else (36, 44, 58) if hov else CARD_BG
            bd_c = KIND_COLORS["solution"] if active else BORDER_STEEL
            pygame.draw.rect(screen, bg_c, p_rect, border_radius=6)
            pygame.draw.rect(screen, bd_c, p_rect, 2 if active else 1, border_radius=6)
            self._text(screen, short_fn, p_rect.center, self.f_tiny_b, TEXT if active else MUTED, center=True)
            self.ui_buttons.append((p_rect, "load_puzzle", (fn, full_path)))
            px += pw + 8

        # Random puzzle generator button
        if HAS_GENERATOR and px + 115 <= BOARD_AREA_W - 10:
            g_rect = pygame.Rect(px, 10, 118, 32)
            g_hov = self.hover_btn == ("gen_puzzle", (7, 7))
            pygame.draw.rect(screen, (42, 88, 68) if g_hov else (30, 64, 50), g_rect, border_radius=6)
            pygame.draw.rect(screen, KIND_COLORS["solution"], g_rect, 1, border_radius=6)
            self._text(screen, "+ NGẪU NHIÊN [G]", g_rect.center, self.f_tiny_b, TEXT, center=True)
            self.ui_buttons.append((g_rect, "gen_puzzle", (7, 7)))

    def _draw_panel(self, screen: pygame.Surface, st: TraceStep):
        px0 = BOARD_AREA_W
        pygame.draw.rect(screen, PANEL_BG, (px0, 0, PANEL_W, WIN_H))
        pygame.draw.line(screen, BORDER_STEEL, (px0, 0), (px0, WIN_H), 2)

        x0 = px0 + 18
        inner_w = PANEL_W - 36
        y = 14

        # 1. Header & Active Puzzle Summary
        self._text(screen, "KAKURO CSP LABORATORY", (x0, y), self.f_title, TEXT)
        self._text(
            screen,
            f"{self.label}  •  Lưới {self.rows}×{self.cols}  •  {len(self.csp.variables)} biến  •  {len(self.csp.runs)} ràng buộc tổng",
            (x0, y + 30), self.f_small, MUTED
        )
        y += 56

        # 2. Interactive Solver Preset Selector Tabs (1 / 2 / 3)
        self._text(screen, "CHẾ ĐỘ THUẬT TOÁN GIẢI (CLICK HOẶC PHÍM 1-3):", (x0, y), self.f_tiny_b, MUTED)
        y += 18
        for idx, p_label in enumerate(PRESET_SHORT):
            tab_rect = pygame.Rect(x0, y, inner_w, 26)
            active = (self.preset_idx == idx)
            hov = self.hover_btn == ("preset", idx)
            bg_c = (38, 62, 98) if active else (34, 42, 56) if hov else CARD_BG
            bd_c = KIND_COLORS["assign"] if active else BORDER_STEEL
            pygame.draw.rect(screen, bg_c, tab_rect, border_radius=5)
            pygame.draw.rect(screen, bd_c, tab_rect, 2 if active else 1, border_radius=5)
            self._text(
                screen, p_label, (x0 + 12, tab_rect.top + 5),
                self.f_small_b if active else self.f_small,
                TEXT if active else MUTED, center=False
            )
            # vertically center text properly
            y += 30
        y += 4

        # 3. Current Step Banner & Interactive Timeline Scrubber
        step_card = pygame.Rect(x0, y, inner_w, 108)
        pygame.draw.rect(screen, CARD_BG, step_card, border_radius=8)
        pygame.draw.rect(screen, BORDER_STEEL, step_card, 1, border_radius=8)

        col = KIND_COLORS.get(st.kind, TEXT)
        badge_rect = pygame.Rect(x0 + 12, y + 10, 235, 24)
        pygame.draw.rect(screen, col, badge_rect, border_radius=4)
        self._text(
            screen, KIND_LABELS_VI.get(st.kind, st.kind.upper()),
            badge_rect.center, self.f_tiny_b, (12, 14, 18), center=True
        )
        self._text(
            screen, f"Bước {self.pos + 1} / {len(self.steps)}",
            (x0 + inner_w - 12, y + 14), self.f_small_b, TEXT, right=True
        )

        # Current step description
        desc_lines = wrap(st.text, 54)[:2]
        for l_idx, line in enumerate(desc_lines):
            self._text(screen, line, (x0 + 12, y + 40 + l_idx * 18), self.f_small, TEXT)

        # Interactive Scrubber Bar with Event Ticks
        bar_x = x0 + 12
        bar_y = y + 82
        bar_w = inner_w - 24
        bar_h = 12
        self.timeline_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(screen, (15, 18, 24), self.timeline_rect, border_radius=6)

        if len(self.steps) > 1:
            fill_w = int(bar_w * self.pos / (len(self.steps) - 1))
        else:
            fill_w = bar_w
        if fill_w > 0:
            pygame.draw.rect(screen, col, (bar_x, bar_y, max(6, fill_w), bar_h), border_radius=6)

        # Draw event markers (conflicts & backtracks & solution) on timeline
        n_steps = max(1, len(self.steps) - 1)
        for idx_s, s_obj in enumerate(self.steps):
            if s_obj.kind in ("conflict", "backtrack", "solution"):
                tx = bar_x + int(bar_w * idx_s / n_steps)
                pygame.draw.line(screen, KIND_COLORS[s_obj.kind], (tx, bar_y - 2), (tx, bar_y + bar_h + 2), 2)

        # Scrubber handle knob
        knob_x = bar_x + fill_w
        pygame.draw.circle(screen, TEXT, (knob_x, bar_y + bar_h // 2), 7)
        pygame.draw.circle(screen, col, (knob_x, bar_y + bar_h // 2), 4)
        y += 116

        # 4. Telemetry Metrics Grid (4 Mini Metric Cards)
        undecided = sum(1 for d in st.domains.values() if len(d) > 1)
        avg_dom = sum(len(d) for d in st.domains.values()) / max(1, len(st.domains))
        metrics = [
            ("GÁN BIẾN / ĐỘ SÂU", f"{st.assigns}  (d={max(0, st.depth)})", KIND_COLORS["assign"]),
            ("LAN TRUYỀN (REVISE)", f"{st.revisions} bước", KIND_COLORS["revise"]),
            ("XUNG ĐỘT / QUAY LUI", f"{st.conflicts} / {st.backtracks}", KIND_COLORS["conflict"]),
            ("Ô CHƯA CHỐT / TB MIỀN", f"{undecided} ô  ({avg_dom:.2f})", KIND_COLORS["solution"]),
        ]
        mw = (inner_w - 8) // 2
        mh = 44
        for m_idx, (m_title, m_val, m_col) in enumerate(metrics):
            mx = x0 + (m_idx % 2) * (mw + 8)
            my = y + (m_idx // 2) * (mh + 6)
            m_rect = pygame.Rect(mx, my, mw, mh)
            pygame.draw.rect(screen, CARD_BG, m_rect, border_radius=6)
            pygame.draw.rect(screen, (45, 54, 68), m_rect, 1, border_radius=6)
            pygame.draw.rect(screen, m_col, (mx, my, 4, mh), border_radius=2)
            self._text(screen, m_title, (mx + 10, my + 5), self.f_tiny_b, MUTED)
            self._text(screen, m_val, (mx + 10, my + 21), self.f_text_b, TEXT)
        y += (mh + 6) * 2 + 4

        ss = self.stats
        self._text(
            screen,
            f"Tổng toàn trình: {ss.nodes} gán biến, {ss.backtracks} quay lui, {ss.seconds * 1000:.1f} ms"
            + (" (đã cắt bớt trace)" if self.truncated else ""),
            (x0, y), self.f_tiny, MUTED
        )
        y += 20

        # 5. Live Cell & Run Inspector OR Recent Trace Log
        insp = self._inspected_cell()
        insp_rect = pygame.Rect(x0, y, inner_w, 128)
        pygame.draw.rect(screen, CARD_BG, insp_rect, border_radius=8)
        pygame.draw.rect(screen, BORDER_STEEL, insp_rect, 1, border_radius=8)

        if insp is not None and insp in st.domains:
            lock_tag = " [ĐÃ GHIM - CLICK ĐỂ BỎ]" if self.selected_cell == insp else " [DI CHUỘT]"
            self._text(
                screen, f"SOI CHI TIẾT Ô (R{insp[0] + 1}, C{insp[1] + 1}){lock_tag}",
                (x0 + 12, y + 7), self.f_tiny_b, (110, 195, 255)
            )
            dom_list = sorted(st.domains[insp])
            self._text(
                screen, f"Miền giá trị hiện tại ({len(dom_list)}): {{{', '.join(map(str, dom_list))}}}",
                (x0 + 12, y + 25), self.f_small_b, TEXT
            )
            ry = y + 46
            for run in self.csp.runs_of.get(insp, []):
                dir_vi = "Ngang (Across →)" if run.direction == "across" else "Dọc (Down ↓)"
                filled = [next(iter(st.domains[c])) for c in run.cells if len(st.domains[c]) == 1]
                rem_sum = run.total - sum(filled)
                rem_len = run.length - len(filled)
                self._text(
                    screen,
                    f"• Dãy {dir_vi}: Tổng = {run.total} ({run.length} ô) | Đã chốt {len(filled)} ô, còn thiếu tổng {rem_sum} ({rem_len} ô)",
                    (x0 + 12, ry), self.f_tiny, MUTED
                )
                # Show surviving combinations count
                combos_str = ", ".join("{" + "".join(map(str, cb)) + "}" for cb in run.combos()[:5])
                if len(run.combos()) > 5:
                    combos_str += f" ... (+{len(run.combos()) - 5} tổ hợp)"
                self._text(screen, f"  Tổ hợp gốc: {combos_str}", (x0 + 12, ry + 16), self.f_tiny, (195, 210, 230))
                ry += 36
        else:
            self._text(
                screen, "NHẬT KÝ BƯỚC GIẢI GẦN ĐÂY (DI CHUỘT LÊN Ô TRẮNG ĐỂ SOI CHI TIẾT):",
                (x0 + 12, y + 7), self.f_tiny_b, (245, 195, 70)
            )
            ry = y + 26
            for i in range(max(0, self.pos - 4), self.pos + 1):
                s_item = self.steps[i]
                is_cur = (i == self.pos)
                pygame.draw.rect(screen, KIND_COLORS[s_item.kind], (x0 + 12, ry + 4, 9, 9), border_radius=2)
                self._text(
                    screen,
                    f"#{i + 1}: " + short(s_item.text, 52),
                    (x0 + 26, ry),
                    self.f_small_b if is_cur else self.f_small,
                    TEXT if is_cur else MUTED
                )
                ry += 19
        y += 136

        # 6. Compact Visual Legend (2 Columns)
        leg_items = [
            (TILE_DECIDED, (55, 120, 235), "Gán bởi Backtracking (TRY)"),
            (TILE_PROPAGATED, (40, 165, 90), "Suy diễn từ Lan truyền (PROP)"),
            ((240, 175, 20), None, "Viền vàng: Dãy đang xét Revise"),
            ((255, 130, 25), None, "Viền cam: Miền vừa thu hẹp"),
        ]
        lw = inner_w // 2
        for idx, (fill_c, badge_c, l_txt) in enumerate(leg_items):
            lx = x0 + (idx % 2) * lw
            ly = y + (idx // 2) * 20
            if badge_c is not None:
                pygame.draw.rect(screen, fill_c, (lx, ly + 2, 14, 14), border_radius=2)
                pygame.draw.rect(screen, badge_c, (lx, ly + 2, 14, 14), 1, border_radius=2)
            else:
                pygame.draw.rect(screen, fill_c, (lx, ly + 2, 14, 14), 2, border_radius=2)
            self._text(screen, l_txt, (lx + 20, ly + 1), self.f_tiny, MUTED)
        y += 46

        # 7. Interactive Playback Transport Controls
        play_lbl = "TẠM DỪNG [SPACE]" if self.playing else "PHÁT TỰ ĐỘNG [SPACE]"
        row1 = [
            ("|<< ĐẦU [R]", "restart", 88),
            ("< LÙI", "step_back", 68),
            (play_lbl, "play_pause", 162),
            ("TIẾN >", "step_fwd", 68),
            ("CUỐI >>|", "jump_end", 62),
        ]
        bx = x0
        for lbl, act, bw in row1:
            b_rect = pygame.Rect(bx, y, bw, 32)
            hov = self.hover_btn == (act, None)
            is_play = (act == "play_pause")
            bg_c = (42, 135, 82) if (is_play and self.playing) else (48, 86, 150) if is_play else (42, 52, 68) if hov else CARD_BG
            pygame.draw.rect(screen, bg_c, b_rect, border_radius=5)
            pygame.draw.rect(screen, (140, 200, 255) if hov or is_play else BORDER_STEEL, b_rect, 1, border_radius=5)
            self._text(screen, lbl, b_rect.center, self.f_tiny_b, TEXT, center=True)
            self.ui_buttons.append((b_rect, act, None))
            bx += bw + 4
        y += 38

        row2 = [
            ("TỚI XUNG ĐỘT [C]", "next_conflict", 138),
            ("TỚI QUAY LUI [B]", "next_backtrack", 138),
            ("- CHẬM", "speed_down", 64),
            (f"{SPEEDS[self.speed_idx]} bước/s", "noop", 66),
            ("+ NHANH", "speed_up", 46),
        ]
        bx = x0
        for lbl, act, bw in row2:
            b_rect = pygame.Rect(bx, y, bw, 28)
            if act == "noop":
                pygame.draw.rect(screen, (15, 18, 24), b_rect, border_radius=4)
                self._text(screen, lbl, b_rect.center, self.f_tiny_b, (245, 195, 70), center=True)
            else:
                hov = self.hover_btn == (act, None)
                pygame.draw.rect(screen, (42, 52, 68) if hov else CARD_BG, b_rect, border_radius=5)
                pygame.draw.rect(screen, BORDER_STEEL, b_rect, 1, border_radius=5)
                self._text(screen, lbl, b_rect.center, self.f_tiny_b, TEXT, center=True)
                self.ui_buttons.append((b_rect, act, None))
            bx += bw + 3
        y += 34

        if self.message:
            self._text(screen, short(self.message, 64), (x0, y), self.f_tiny_b, self.msg_color)

    def _draw_menu_modal(self, screen: pygame.Surface):
        """Draws a full-featured Puzzle & Solver Mode Selection Hub Modal."""
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((8, 11, 16, 210))
        screen.blit(overlay, (0, 0))

        mw, mh = 860, 560
        mx = (WIN_W - mw) // 2
        my = (WIN_H - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(screen, (20, 25, 34), modal_rect, border_radius=12)
        pygame.draw.rect(screen, (95, 145, 225), modal_rect, 2, border_radius=12)

        self._text(screen, "TRUNG TÂM LỰA CHỌN BÀN CỜ & CHẾ ĐỘ GIẢI KAKURO", (mx + 26, my + 20), self.f_title, TEXT)
        self._text(
            screen,
            "Chọn bàn cờ có sẵn, sinh ngẫu nhiên bàn cờ mới hoặc cấu hình thuật toán CSP trước khi quan sát",
            (mx + 26, my + 50), self.f_small, MUTED
        )

        close_rect = pygame.Rect(mx + mw - 120, my + 18, 96, 34)
        pygame.draw.rect(screen, (65, 78, 98), close_rect, border_radius=6)
        self._text(screen, "ĐÓNG [ESC]", close_rect.center, self.f_tiny_b, TEXT, center=True)
        self.ui_buttons.append((close_rect, "close_menu", None))

        # Section 1: Available Puzzles Cards
        self._text(screen, "1. CHỌN BÀN CỜ KAKURO:", (mx + 26, my + 90), self.f_small_b, (245, 195, 70))
        card_w = (mw - 76) // 3
        card_h = 140
        for idx, (fn, full_path) in enumerate(self.available_puzzles[:6]):
            cx = mx + 26 + (idx % 3) * (card_w + 12)
            cy = my + 116 + (idx // 3) * (card_h + 12)
            c_rect = pygame.Rect(cx, cy, card_w, card_h)
            active = (self.label == fn)
            hov = self.hover_btn == ("load_puzzle", (fn, full_path))
            pygame.draw.rect(screen, (36, 52, 76) if active else (32, 40, 54) if hov else CARD_BG, c_rect, border_radius=8)
            pygame.draw.rect(screen, KIND_COLORS["solution"] if active else (95, 145, 225) if hov else BORDER_STEEL, c_rect, 2 if active else 1, border_radius=8)

            self._text(screen, fn, (cx + 14, cy + 12), self.f_text_b, TEXT)
            try:
                pz = KakuroPuzzle.from_text(open(full_path).read())
                info_1 = f"Kích thước: {pz.rows} × {pz.cols}"
                info_2 = f"Số ô trắng (biến): {len(pz.white)} ô"
                info_3 = f"Số dãy ràng buộc (runs): {len(pz.runs)} dãy"
            except Exception:
                info_1, info_2, info_3 = "File puzzle .txt", "", ""
            self._text(screen, info_1, (cx + 14, cy + 42), self.f_small, MUTED)
            self._text(screen, info_2, (cx + 14, cy + 64), self.f_small, MUTED)
            self._text(screen, info_3, (cx + 14, cy + 86), self.f_small, MUTED)
            self._text(
                screen, "ĐANG MỞ" if active else "CLICK ĐỂ NẠP BÀN CỜ →",
                (cx + 14, cy + 112), self.f_tiny_b,
                KIND_COLORS["solution"] if active else (120, 190, 255)
            )
            self.ui_buttons.append((c_rect, "load_puzzle", (fn, full_path)))

        # Section 2: Random Generator & Custom File Loader
        gen_y = my + 278
        self._text(screen, "2. SINH BÀN CỜ MỚI HOẶC TẢI FILE NGOÀI:", (mx + 26, gen_y), self.f_small_b, (245, 195, 70))
        gen_btns = [
            ("SINH BÀN CỜ 6×6 NGẪU NHIÊN", "gen_puzzle", (6, 6)),
            ("SINH BÀN CỜ 7×7 NGẪU NHIÊN", "gen_puzzle", (7, 7)),
            ("SINH BÀN CỜ 8×8 NGẪU NHIÊN", "gen_puzzle", (8, 8)),
            ("MỞ FILE .TXT TỪ MÁY [L]", "open_file", None),
        ]
        gb_w = (mw - 88) // 4
        for idx, (lbl, act, payload) in enumerate(gen_btns):
            gx = mx + 26 + idx * (gb_w + 12)
            g_rect = pygame.Rect(gx, gen_y + 24, gb_w, 42)
            hov = self.hover_btn == (act, payload)
            pygame.draw.rect(screen, (42, 82, 68) if hov else (28, 56, 48), g_rect, border_radius=7)
            pygame.draw.rect(screen, KIND_COLORS["solution"], g_rect, 1, border_radius=7)
            self._text(screen, lbl, g_rect.center, self.f_tiny_b, TEXT, center=True)
            self.ui_buttons.append((g_rect, act, payload))

        # Section 3: Algorithm Preset Cards
        alg_y = my + 362
        self._text(screen, "3. CHỌN CẤU HÌNH THUẬT TOÁN CSP SOLVER:", (mx + 26, alg_y), self.f_small_b, (245, 195, 70))
        alg_descs = [
            ("Full: Propagation + MRV + Degree + LCV", "Tối ưu nhất: Lan truyền ràng buộc kết hợp chọn biến MRV/Degree và thứ tự giá trị LCV."),
            ("Propagation + Thứ tự biến tĩnh", "Chỉ bật lan truyền ràng buộc (All-Diff + lọc tổ hợp tổng), duyệt biến theo thứ tự cố định."),
            ("Backtracking thuần túy (Tắt Propagation)", "Quay lui cổ điển không thu hẹp miền trước — minh họa trực quan hiện tượng bùng nổ nhánh và quay lui."),
        ]
        for idx, (a_title, a_desc) in enumerate(alg_descs):
            ay = alg_y + 24 + idx * 50
            a_rect = pygame.Rect(mx + 26, ay, mw - 52, 44)
            active = (self.preset_idx == idx)
            hov = self.hover_btn == ("preset", idx)
            pygame.draw.rect(screen, (38, 60, 96) if active else (32, 40, 54) if hov else CARD_BG, a_rect, border_radius=7)
            pygame.draw.rect(screen, KIND_COLORS["assign"] if active else BORDER_STEEL, a_rect, 2 if active else 1, border_radius=7)
            self._text(screen, f"[{idx + 1}] {a_title}", (mx + 42, ay + 6), self.f_small_b, TEXT)
            self._text(screen, a_desc, (mx + 42, ay + 24), self.f_tiny, MUTED)
            self.ui_buttons.append((a_rect, "preset", idx))


def main(argv=None):
    path = argv if argv is not None else sys.argv[1:]
    path = (
        path[0]
        if path
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles", "complex_9x9.txt")
    )
    pygame.init()
    app = KakuroApp(open(path).read(), os.path.basename(path))
    screen = pygame.display.set_mode(app.size)
    pygame.display.set_caption("Kakuro CSP Studio - Domains, Constraint Propagation & Backtracking")
    clock = pygame.time.Clock()
    size = app.size
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or app.handle(event) == "quit":
                running = False
                break
        if app.size != size:
            size = app.size
            screen = pygame.display.set_mode(size)
        app.update()
        app.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
