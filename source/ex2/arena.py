"""Task 2 - Requirement 3: game controller / arena (no PyGame dependency).

GameController runs one game between two players (human or agent). Agents are executed
in a worker thread so that the GUI never freezes, and every agent receives a PRIVATE COPY
of the state. Rules enforced on every agent (human GUI included):
  * time limit per move: if exceeded the move is replaced by STAY, and the agent is
    skipped (STAY) until its late computation finishes (its object is never run twice at once);
  * exceptions or non-Action results are replaced by STAY and counted.

Command line (headless tournament between two agents, both sides, several openings):
    python arena.py agents/example_greedy_agent.py hab --games 3
Agent tokens: a path to a .py plugin, or one of: random, minimax, alphabeta, hminimax, hab
"""
import argparse
import random
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from tank_game import Action, GameState, MAX_PLAYER, MIN_PLAYER
from tank_ai import Agent, RandomAgent, SearchAgent


@dataclass
class PlayerStats:
    moves: int = 0
    total_time: float = 0.0
    max_time: float = 0.0
    timeouts: int = 0
    skipped_busy: int = 0
    invalid: int = 0
    errors: int = 0
    last_error: str = ""

    @property
    def avg_time(self) -> float:
        return self.total_time / self.moves if self.moves else 0.0


class MoveRequest:
    """Runs agent.choose_action(state_copy) in a daemon thread."""

    def __init__(self, agent: Agent, state: GameState, time_limit: float):
        self.time_limit = time_limit
        self.start = time.perf_counter()
        self.result = None
        self.error: Optional[str] = None
        self.elapsed: Optional[float] = None
        self._event = threading.Event()
        self.thread = threading.Thread(target=self._run, args=(agent, state.copy()),
                                       daemon=True)
        self.thread.start()

    def _run(self, agent, state):
        try:
            self.result = agent.choose_action(state)
        except Exception as e:                                 # a plugin must not crash the game
            self.error = repr(e)
        finally:
            self.elapsed = time.perf_counter() - self.start
            self._event.set()

    @property
    def done(self) -> bool:
        return self._event.is_set()

    @property
    def timed_out(self) -> bool:
        return not self.done and time.perf_counter() - self.start > self.time_limit

    def wait(self, timeout: float):
        self._event.wait(timeout)


@dataclass
class PlayerSlot:
    name: str
    agent: Optional[Agent]                  # None => human
    stats: PlayerStats = field(default_factory=PlayerStats)
    request: Optional[MoveRequest] = None
    zombie: Optional[MoveRequest] = None    # a timed-out computation still running
    last_action: Optional[Action] = None
    last_think: float = 0.0

    @property
    def is_human(self) -> bool:
        return self.agent is None


class GameController:
    def __init__(self, agent0: Optional[Agent], agent1: Optional[Agent],
                 name0: str = None, name1: str = None, time_limit: float = 3.0,
                 initial_state: GameState = None):
        self.slots = [
            PlayerSlot(name0 or (agent0.name if agent0 else "Human"), agent0),
            PlayerSlot(name1 or (agent1.name if agent1 else "Human"), agent1)]
        self.time_limit = time_limit
        self.state = initial_state or GameState.initial()
        self.history = []                       # (cycle, player, action)

    # ------------------------------------------------------------------ queries
    @property
    def over(self) -> bool:
        return self.state.is_terminal()

    @property
    def current(self) -> PlayerSlot:
        return self.slots[self.state.to_move]

    def needs_human(self) -> bool:
        return not self.over and self.current.is_human

    def result(self) -> int:
        """+1 player 0 (MAX) wins, -1 player 1 wins, 0 draw (valid once over)."""
        u = self.state.utility()
        return (u > 0) - (u < 0)

    # ----------------------------------------------------------------- applying
    def _apply(self, action: Action, slot: PlayerSlot, think: float = 0.0):
        slot.last_action, slot.last_think = action, think
        self.history.append((self.state.cycle, self.state.to_move, action))
        self.state = self.state.apply(action)

    def submit_human_action(self, action: Action) -> bool:
        if not self.needs_human() or not isinstance(action, Action):
            return False
        self._apply(action, self.current)
        return True

    def update(self, can_apply: bool = True) -> bool:
        """Non-blocking step. Starts the agent computation if needed; applies its move
        when finished (and `can_apply`). Returns True if an action was applied."""
        if self.over or self.current.is_human:
            return False
        slot = self.current
        st = slot.stats

        if slot.request is None:
            if slot.zombie is not None and not slot.zombie.done:
                st.skipped_busy += 1                            # still busy with an old move
                self._apply(Action.STAY, slot)
                return True
            slot.zombie = None
            slot.request = MoveRequest(slot.agent, self.state, self.time_limit)

        req = slot.request
        if req.timed_out:
            st.timeouts += 1
            slot.zombie, slot.request = req, None
            self._apply(Action.STAY, slot, req.time_limit)
            return True
        if not req.done or not can_apply:
            return False

        slot.request = None
        action = req.result
        if req.error is not None:
            st.errors += 1
            st.last_error = req.error
            action = Action.STAY
        elif not isinstance(action, Action):
            st.invalid += 1
            action = Action.STAY
        st.moves += 1
        st.total_time += req.elapsed
        st.max_time = max(st.max_time, req.elapsed)
        self._apply(action, slot, req.elapsed)
        return True

    def wait_for_agent(self, timeout: float = 0.01):
        slot = self.current
        if slot.request is not None:
            slot.request.wait(timeout)


# ------------------------------------------------------------------------ headless
def run_match(agent0: Agent, agent1: Agent, state: GameState = None,
              time_limit: float = 3.0, max_cycles: int = 150):
    """Plays a full game without a GUI. Returns (controller, result)."""
    ctrl = GameController(agent0, agent1, time_limit=time_limit, initial_state=state)
    while not ctrl.over and ctrl.state.cycle < max_cycles:
        if not ctrl.update():
            ctrl.wait_for_agent(0.01)
    return ctrl, (ctrl.result() if ctrl.over else 0)


def random_openings(count: int, seed: int = 11) -> List[GameState]:
    rng = random.Random(seed)
    out = [GameState.initial()]
    while len(out) < count:
        s = GameState.initial()
        for _ in range(2 * rng.randint(1, 3)):
            s = s.apply(rng.choice(s.legal_actions()))
        out.append(s)
    return out


def head_to_head(factory_a, factory_b, games: int = 3, time_limit: float = 3.0,
                 max_cycles: int = 150):
    """A vs B from `games` openings, each played with sides swapped.
    factory_x() must return a fresh agent. Returns a dict of results."""
    res = {"A_wins": 0, "B_wins": 0, "draws": 0, "cycles": [],
           "A_stats": PlayerStats(), "B_stats": PlayerStats()}
    for op in random_openings(games):
        for a_is_max in (True, False):
            a, b = factory_a(), factory_b()
            ctrl, r = run_match(*( (a, b) if a_is_max else (b, a) ),
                                state=op, time_limit=time_limit, max_cycles=max_cycles)
            a_slot = ctrl.slots[0 if a_is_max else 1]
            b_slot = ctrl.slots[1 if a_is_max else 0]
            a_result = r if a_is_max else -r
            res["A_wins"] += a_result == 1
            res["B_wins"] += a_result == -1
            res["draws"] += a_result == 0
            res["cycles"].append(ctrl.state.cycle)
            for tag, slot in (("A_stats", a_slot), ("B_stats", b_slot)):
                s, t = res[tag], slot.stats
                s.moves += t.moves
                s.total_time += t.total_time
                s.max_time = max(s.max_time, t.max_time)
                s.timeouts += t.timeouts
                s.errors += t.errors
                s.invalid += t.invalid
    return res


# ---------------------------------------------------------------------------- CLI
def _factory_from_token(token: str):
    key = token.lower()
    builtin = {
        "random": lambda: RandomAgent(),
        "minimax": lambda: SearchAgent("Minimax", 4, time_limit=1.0),
        "alphabeta": lambda: SearchAgent("Alpha-Beta", 4, time_limit=1.0),
        "hminimax": lambda: SearchAgent("Heuristic Minimax", 4, time_limit=1.0),
        "hab": lambda: SearchAgent("Heuristic Minimax + Alpha-Beta", 4, time_limit=1.0),
    }
    if key in builtin:
        return builtin[key], key
    from agent_loader import load_agent_from_file
    load_agent_from_file(token)                              # fail early with a clear error
    return (lambda: load_agent_from_file(token, validate=False)), token


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Headless Tank Battle arena")
    ap.add_argument("agent_a")
    ap.add_argument("agent_b")
    ap.add_argument("--games", type=int, default=3, help="openings (each played on both sides)")
    ap.add_argument("--time-limit", type=float, default=3.0)
    args = ap.parse_args()
    fa, na = _factory_from_token(args.agent_a)
    fb, nb = _factory_from_token(args.agent_b)
    r = head_to_head(fa, fb, args.games, args.time_limit)
    n = len(r["cycles"])
    print(f"A = {na}   B = {nb}   ({n} games)")
    print(f"A wins {r['A_wins']} | B wins {r['B_wins']} | draws {r['draws']} | "
          f"avg cycles {sum(r['cycles']) / n:.1f}")
    for tag in ("A_stats", "B_stats"):
        s = r[tag]
        print(f"{tag[0]}: avg think {s.avg_time * 1000:.2f} ms, max {s.max_time * 1000:.1f} ms, "
              f"timeouts {s.timeouts}, errors {s.errors}, invalid {s.invalid}")