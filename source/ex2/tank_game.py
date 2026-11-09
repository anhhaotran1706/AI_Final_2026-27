"""Task 2 - Requirement 1: Tank Battle formulated as a two-player zero-sum game.

Components
----------
Players      : 0 = MAX (our tank), 1 = MIN (opponent). U_MIN = -U_MAX.
State        : GameState (walls, tanks, bases, bullets, player to move, cycle number)
Actions      : Action enum (MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY)
Transition   : GameState.apply(action) -> new GameState
Terminal     : GameState.is_terminal()
Utility      : GameState.utility()   (from MAX's point of view)

Design decisions (not specified in the assignment):
  * Coordinates are (x, y); x grows to the right, y grows downwards; (0, 0) is top-left.
  * A game cycle = MAX acts, then MIN acts, then bullets are processed.
    In the search tree each action is one ply, so a cycle = 2 plies.
  * Moving: the tank always turns to face the chosen direction; it moves one cell only
    if the target cell is inside the board and empty (no wall, tank or base).
  * FIRE: creates a bullet in the tank's cell, flying in the tank's facing direction.
    A tank may have at most ONE bullet in flight (FIRE is illegal while its bullet flies).
  * Bullets: moved cell by cell, up to 3 cells per cycle; after each cell the collision
    is checked; a bullet disappears when it hits a wall / tank / base (1 damage) or leaves
    the board. Bullets do not collide with each other.
  * Terminal: a tank or a base has HP <= 0 (checked at the end of a cycle), or the
    cycle limit is reached (draw).
  * Utility: win = +WIN - cycle (faster win is better), loss = -(WIN - cycle), draw = 0.
    If both sides lose a tank/base in the same cycle -> draw.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

Pos = Tuple[int, int]

MAX_PLAYER, MIN_PLAYER = 0, 1
TANK_HP, BASE_HP, WALL_HP = 6, 9, 3
BULLET_SPEED = 3
WIN = 1000
MAX_CYCLES = 200

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class Action(Enum):
    MOVE_UP = 0
    MOVE_DOWN = 1
    MOVE_LEFT = 2
    MOVE_RIGHT = 3
    FIRE = 4
    STAY = 5

ACTION_DIR = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
    Action.MOVE_RIGHT: Direction.RIGHT,
}

@dataclass
class Tank:
    pos: Pos
    facing: Direction
    hp: int = TANK_HP #đã check

@dataclass
class Base:
    pos: Pos
    hp: int = BASE_HP

@dataclass
class Bullet:
    pos: Pos
    direction: Direction
    owner: int

class GameConfig:
    """Board size and initial layout. The default map is point-symmetric (fair)."""

    def __init__(self, width=13, height=13, walls=None, tank_pos=None, base_pos=None):
        self.width, self.height = width, height
        self.walls = walls if walls is not None else self._default_walls(width, height)
        self.tank_pos = tank_pos or [(width // 2, height - 3), (width // 2, 2)]
        self.base_pos = base_pos or [(width // 2, height - 1), (width // 2, 0)]

    @staticmethod
    def _default_walls(w, h):
        half = [(5, 0), (7, 0), (5, 1), (6, 1), (7, 1),       # protect the top base
                (2, 3), (3, 3), (9, 3), (10, 3), (6, 4), (4, 5), (8, 5), (6, 6)]
        cells = set(half) | {(w - 1 - x, h - 1 - y) for x, y in half}   # 180-degree mirror
        return sorted(cells) #đã check


class GameState:
    __slots__ = ("cfg", "walls", "tanks", "bases", "bullets", "to_move", "cycle")

    def __init__(self, cfg, walls, tanks, bases, bullets, to_move=0, cycle=0):
        self.cfg = cfg
        self.walls: Dict[Pos, int] = walls
        self.tanks: List[Tank] = tanks
        self.bases: List[Base] = bases
        self.bullets: List[Bullet] = bullets
        self.to_move = to_move
        self.cycle = cycle

    # ------------------------------------------------------------ construction
    @staticmethod
    def initial(cfg: GameConfig = None) -> "GameState":
        cfg = cfg or GameConfig()
        tanks = [Tank(cfg.tank_pos[0], Direction.UP), Tank(cfg.tank_pos[1], Direction.DOWN)]
        bases = [Base(cfg.base_pos[0]), Base(cfg.base_pos[1])]
        walls = {p: WALL_HP for p in cfg.walls}
        return GameState(cfg, walls, tanks, bases, [])

    def copy(self) -> "GameState":
        return GameState(self.cfg, dict(self.walls),
                         [Tank(t.pos, t.facing, t.hp) for t in self.tanks],
                         [Base(b.pos, b.hp) for b in self.bases],
                         [Bullet(b.pos, b.direction, b.owner) for b in self.bullets],
                         self.to_move, self.cycle) #đã check

    # ------------------------------------------------------------------ queries
    def in_bounds(self, p: Pos) -> bool:
        return 0 <= p[0] < self.cfg.width and 0 <= p[1] < self.cfg.height

    def is_free(self, p: Pos) -> bool:
        """Cell can be entered by a moving tank."""
        if not self.in_bounds(p) or p in self.walls:
            return False
        if any(t.hp > 0 and t.pos == p for t in self.tanks):
            return False
        return not any(b.pos == p for b in self.bases)

    def has_bullet_in_flight(self, player: int) -> bool:
        return any(b.owner == player for b in self.bullets) #đã check

    # ------------------------------------------------------------------ actions
    def legal_actions(self, player: int = None) -> List[Action]:
        """Actions that change the state (no-op moves such as bumping into a wall while
        already facing it are removed to reduce the branching factor). STAY is always legal."""
        player = self.to_move if player is None else player
        tank = self.tanks[player]
        acts = []
        for a, d in ACTION_DIR.items():
            target = (tank.pos[0] + d.value[0], tank.pos[1] + d.value[1])
            if self.is_free(target) or tank.facing != d:   # moves, or at least turns
                acts.append(a)
        if not self.has_bullet_in_flight(player):
            acts.append(Action.FIRE)
        acts.append(Action.STAY)
        return acts #đã check

    # --------------------------------------------------------------- transition
    def apply(self, action: Action) -> "GameState":
        """Result(s, a): returns a NEW state."""
        s = self.copy()
        p = s.to_move
        tank = s.tanks[p]
        if action in ACTION_DIR:
            d = ACTION_DIR[action]
            tank.facing = d
            target = (tank.pos[0] + d.value[0], tank.pos[1] + d.value[1])
            if s.is_free(target):
                tank.pos = target
        elif action == Action.FIRE and not s.has_bullet_in_flight(p):
            s.bullets.append(Bullet(tank.pos, tank.facing, p))
        # STAY: nothing

        if p == MAX_PLAYER:
            s.to_move = MIN_PLAYER
        else:                                   # end of game cycle
            s._move_bullets()
            s.to_move = MAX_PLAYER
            s.cycle += 1
        return s #đã check

    def _move_bullets(self):
        alive = []
        for b in self.bullets:
            hit = False
            for _ in range(BULLET_SPEED):
                b.pos = (b.pos[0] + b.direction.value[0], b.pos[1] + b.direction.value[1])
                if not self.in_bounds(b.pos):
                    hit = True                  # left the board
                    break
                if b.pos in self.walls:
                    self.walls[b.pos] -= 1
                    if self.walls[b.pos] <= 0:
                        del self.walls[b.pos]
                    hit = True
                    break
                target = next((t for t in self.tanks if t.hp > 0 and t.pos == b.pos), None)
                if target:
                    target.hp -= 1
                    hit = True
                    break
                base = next((x for x in self.bases if x.pos == b.pos), None)
                if base:
                    base.hp -= 1
                    hit = True
                    break
            if not hit:
                alive.append(b)
        self.bullets = alive #đã check

    # ----------------------------------------------------------------- terminal
    def _destroyed(self, player: int) -> bool:
        return self.tanks[player].hp <= 0 or self.bases[player].hp <= 0

    def is_terminal(self) -> bool:
        # outcome is only decided at the end of a cycle (after bullets were processed)
        if self.to_move != MAX_PLAYER:
            return False
        return (self._destroyed(MAX_PLAYER) or self._destroyed(MIN_PLAYER)
                or self.cycle >= MAX_CYCLES)#đã check

    def utility(self) -> int:
        """Utility from MAX's point of view (only meaningful at terminal states)."""
        lose, win = self._destroyed(MAX_PLAYER), self._destroyed(MIN_PLAYER)
        if lose == win:
            return 0                            # draw (both destroyed or cycle limit)
        value = WIN - self.cycle
        return value if win else -value  #đã check số điểm value

    # -------------------------------------------------------------------- utils
    def key(self):
        """Hashable representation (for transposition tables)."""
        return (tuple(sorted(self.walls.items())),
                tuple((t.pos, t.facing, t.hp) for t in self.tanks),
                tuple(b.hp for b in self.bases),
                tuple(sorted((b.pos, b.direction, b.owner) for b in self.bullets)),
                self.to_move)

    def render(self) -> str:
        """ASCII view: digits = walls (HP), B/b = bases, A/E = our/enemy tank, * = bullet."""
        grid = [["." for _ in range(self.cfg.width)] for _ in range(self.cfg.height)]
        for (x, y), hp in self.walls.items():
            grid[y][x] = str(hp)
        for i, b in enumerate(self.bases):
            grid[b.pos[1]][b.pos[0]] = "B" if i == MAX_PLAYER else "b"
        for i, t in enumerate(self.tanks):
            if t.hp > 0:
                grid[t.pos[1]][t.pos[0]] = "A" if i == MAX_PLAYER else "E"
        for b in self.bullets:
            if self.in_bounds(b.pos):
                grid[b.pos[1]][b.pos[0]] = "*"
        head = (f"cycle={self.cycle} tankHP={[t.hp for t in self.tanks]} "
                f"baseHP={[b.hp for b in self.bases]}")
        return head + "\n" + "\n".join(" ".join(r) for r in grid) #đã check


if __name__ == "__main__":
    s = GameState.initial()
    print(s.render())
    print("MAX legal actions:", [a.name for a in s.legal_actions()])