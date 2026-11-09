"""Task 2 - Requirement 2: adversarial search agents for the Tank Battle game.

Four configurations (all depth-limited, depth counted in plies):
    1. Minimax                          use_alpha_beta=False, use_heuristic=False
    2. Alpha-Beta                       use_alpha_beta=True,  use_heuristic=False
    3. Heuristic Minimax                use_alpha_beta=False, use_heuristic=True
    4. Heuristic Minimax + Alpha-Beta   use_alpha_beta=True,  use_heuristic=True

Without a heuristic, a non-terminal leaf is valued 0 (unknown outcome).
With a heuristic, a non-terminal leaf is valued by HeuristicEvaluator.

Values are always computed from the point of view of the agent's own player ("me"),
so the same code controls either tank.

Optimisations:
  * the SAME move ordering is used by all four configurations (so that Minimax and
    Alpha-Beta return exactly the same value and action, and the only difference is
    the amount of work); ordering is what makes pruning effective.
  * no-op actions are removed in GameState.legal_actions().
  * optional iterative deepening with a per-move time limit (real-time play).
"""
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tank_game import (ACTION_DIR, Action, Direction, GameState, MAX_PLAYER,
                       MIN_PLAYER, WIN)

INF = float("inf")

@dataclass
class SearchStats:
    nodes: int = 0         
    leaves: int = 0         
    cutoffs: int = 0        
    depth: int = 0          
    seconds: float = 0.0
    value: float = 0.0      

class TimeUp(Exception):
    pass

#xác định vật thể đầu tiên mà viên đạn gặp
def first_hit(s: GameState, pos, direction: Direction):
    dx, dy = direction.value
    x, y = pos
    while True:
        x, y = x + dx, y + dy
        p = (x, y)
        if not s.in_bounds(p):
            return None
        if p in s.walls:
            return ("wall", None)
        for i, t in enumerate(s.tanks):
            if t.hp > 0 and t.pos == p:
                return ("tank", i)
        for i, b in enumerate(s.bases):
            if b.pos == p:
                return ("base", i) #đã check 

class HeuristicEvaluator:
    W_TANK, W_BASE = 40, 25
    W_AIM_TANK, W_AIM_BASE = 30, 25
    W_BULLET_TANK, W_BULLET_BASE = 35, 30
    W_DIST = 2

    def __init__(self, weights: dict = None):
        for k, v in (weights or {}).items():
            setattr(self, k, v)

    def _aim(self, s, p):
        tank = s.tanks[p]
        if tank.hp <= 0:
            return 0
        can_fire = 1.0 if not s.has_bullet_in_flight(p) else 0.5
        total = 0.0
        for d in Direction:
            hit = first_hit(s, tank.pos, d)
            if not hit or hit[1] == p:
                continue
            w = (self.W_AIM_TANK if hit[0] == "tank"
                 else self.W_AIM_BASE if hit[0] == "base" else 0)
            total += w * can_fire * (1.0 if d == tank.facing else 1 / 3)
        return total # đã check

    def evaluate(self, s: GameState, me: int) -> float:
        opp = 1 - me
        score = (self.W_TANK * (s.tanks[me].hp - s.tanks[opp].hp)
                 + self.W_BASE * (s.bases[me].hp - s.bases[opp].hp))
        score += self._aim(s, me) - self._aim(s, opp)
        for b in s.bullets:
            hit = first_hit(s, b.pos, b.direction)
            if not hit or hit[0] == "wall":
                continue
            impact = self.W_BULLET_TANK if hit[0] == "tank" else self.W_BULLET_BASE
            gain = impact if hit[1] != b.owner else -impact      # friendly fire is bad
            score += gain if b.owner == me else -gain
        bx, by = s.bases[opp].pos
        tx, ty = s.tanks[me].pos
        score -= self.W_DIST * (abs(bx - tx) + abs(by - ty))
        return max(-900.0, min(900.0, score)) # đã check
    
class Searcher:
    def __init__(self, depth, use_alpha_beta, use_heuristic, evaluator=None):
        self.depth = depth
        self.use_ab = use_alpha_beta
        self.use_heuristic = use_heuristic
        self.evaluator = evaluator or HeuristicEvaluator()
        self.stats = SearchStats()
        self.me = MAX_PLAYER
        self._deadline = None

    @staticmethod
    def ordered_actions(s: GameState):
        p = s.to_move
        tank = s.tanks[p]
        tx, ty = s.bases[1 - p].pos
        acts = s.legal_actions(p)

        def key(a):
            if a == Action.FIRE:
                return -1
            if a == Action.STAY:
                return 10_000
            d = ACTION_DIR[a].value
            np_ = (tank.pos[0] + d[0], tank.pos[1] + d[1])
            if not s.is_free(np_):
                np_ = tank.pos
            return abs(np_[0] - tx) + abs(np_[1] - ty)

        return sorted(acts, key=key) # đã check
    
    def _value(self, s, depth, alpha, beta):
        st = self.stats
        st.nodes += 1
        if self._deadline is not None and (st.nodes & 255) == 0 \
                and time.perf_counter() > self._deadline:
            raise TimeUp
        if s.is_terminal():
            u = s.utility()
            return u if self.me == MAX_PLAYER else -u
        if depth == 0:
            st.leaves += 1
            return self.evaluator.evaluate(s, self.me) if self.use_heuristic else 0

        maximizing = s.to_move == self.me
        best = -INF if maximizing else INF
        for a in self.ordered_actions(s):
            v = self._value(s.apply(a), depth - 1, alpha, beta)
            if maximizing:
                if v > best:
                    best = v
                if self.use_ab:
                    alpha = max(alpha, best)
            else:
                if v < best:
                    best = v
                if self.use_ab:
                    beta = min(beta, best)
            if self.use_ab and alpha >= beta:
                st.cutoffs += 1
                break
        return best #đã check

    def _root(self, s, depth):
        best_a, best_v = None, -INF
        alpha = -INF
        for a in self.ordered_actions(s):
            v = self._value(s.apply(a), depth - 1, alpha, INF)
            if v > best_v:
                best_v, best_a = v, a
            if self.use_ab:
                alpha = max(alpha, best_v)
        return best_a, best_v

    def search(self, s: GameState, time_limit: float = None):
        """Returns (best_action, SearchStats). With time_limit: iterative deepening up to
        self.depth, keeping the result of the last fully completed depth."""
        self.me = s.to_move
        self.stats = SearchStats()
        t0 = time.perf_counter()
        self._deadline = t0 + time_limit if time_limit else None
        best_a, best_v, done = None, 0.0, 0
        depths = range(1, self.depth + 1) if time_limit else [self.depth]
        try:
            for d in depths:
                best_a, best_v = self._root(s, d)
                done = d
        except TimeUp:
            pass
        if best_a is None:                       # timed out before depth 1 finished
            best_a = s.legal_actions()[0]
        self.stats.depth, self.stats.value = done, best_v
        self.stats.seconds = time.perf_counter() - t0
        return best_a, self.stats #đã check


# ---------------------------------------------------------------------------- agents
class Agent(ABC):
    name = "agent"

    @abstractmethod
    def choose_action(self, state: GameState) -> Action:
        """Choose an action for the player whose turn it is (state.to_move)."""


class RandomAgent(Agent):
    name = "random"

    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def choose_action(self, state):
        return self.rng.choice(state.legal_actions())


class SearchAgent(Agent):
    CONFIGS = {
        "Minimax": (False, False),
        "Alpha-Beta": (True, False),
        "Heuristic Minimax": (False, True),
        "Heuristic Minimax + Alpha-Beta": (True, True), #đã check
    }

    def __init__(self, config_name="Heuristic Minimax + Alpha-Beta", depth=4,
                 time_limit=None, evaluator=None):
        ab, heur = self.CONFIGS[config_name]
        self.name = f"{config_name} (d={depth})"
        self.searcher = Searcher(depth, ab, heur, evaluator)
        self.time_limit = time_limit
        self.last_stats = None

    def choose_action(self, state):
        action, self.last_stats = self.searcher.search(state, self.time_limit)
        return action #đã check