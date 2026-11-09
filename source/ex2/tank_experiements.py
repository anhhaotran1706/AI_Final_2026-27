"""Task 2 - Requirement 2: experiments for the four search configurations.

Exp A  Computational cost: same scenarios, same depths, for all four configurations.
       Metrics: explored states, execution time, alpha-beta cutoffs, and a correctness
       check (Alpha-Beta must return the same value/action as Minimax).
Exp B  Search depth reachable under a fixed time budget per move (iterative deepening).
Exp C  Playing strength: round-robin matches at equal depth from several openings.

Run:  python tank_experiments.py
"""
import csv
import random
import statistics
import time

from tank_game import GameState, MAX_PLAYER, MIN_PLAYER
from tank_ai import SearchAgent, Searcher

CONFIG_NAMES = list(SearchAgent.CONFIGS.keys())


# ---------------------------------------------------------------------- scenarios
def make_scenarios(count=10, seed=2024):
    """Initial state + `count-1` reproducible mid-game states (random play)."""
    rng = random.Random(seed)
    scenarios = [("initial", GameState.initial())]
    while len(scenarios) < count:
        s = GameState.initial()
        k = rng.randint(2, 30)
        for _ in range(2 * k):
            if s.is_terminal():
                break
            s = s.apply(rng.choice(s.legal_actions()))
        if not s.is_terminal():
            scenarios.append((f"mid-{len(scenarios)}(c{s.cycle})", s))
    return scenarios


def write_csv(path, rows):
    if rows:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)#đã check


# ------------------------------------------------------------------------- Exp A
def experiment_cost(depths=(2, 3, 4, 5, 6), scenarios=None):
    scenarios = scenarios or make_scenarios()
    rows, mismatches = [], 0
    for d in depths:
        per_cfg = {n: {"nodes": [], "time": [], "cut": []} for n in CONFIG_NAMES}
        for _, s in scenarios:
            results = {}
            for name in CONFIG_NAMES:
                ab, heur = SearchAgent.CONFIGS[name]
                a, st = Searcher(d, ab, heur).search(s)
                results[name] = (a, st.value)
                per_cfg[name]["nodes"].append(st.nodes)
                per_cfg[name]["time"].append(st.seconds)
                per_cfg[name]["cut"].append(st.cutoffs)
            # correctness: pruning must not change the result
            mismatches += results["Minimax"] != results["Alpha-Beta"]
            mismatches += (results["Heuristic Minimax"]
                           != results["Heuristic Minimax + Alpha-Beta"])
        for name in CONFIG_NAMES:
            m = per_cfg[name]
            rows.append({"depth": d, "config": name,
                         "avg_nodes": round(statistics.mean(m["nodes"]), 1),
                         "avg_time_s": round(statistics.mean(m["time"]), 5),
                         "avg_cutoffs": round(statistics.mean(m["cut"]), 1)})
            print(f"d={d} {name:<32} nodes={rows[-1]['avg_nodes']:<10} "
                  f"time={rows[-1]['avg_time_s']:<9} cutoffs={rows[-1]['avg_cutoffs']}")
    print("Correctness check (Alpha-Beta == Minimax): mismatches =", mismatches)
    return rows #đã check


# ------------------------------------------------------------------------- Exp B
def experiment_depth_budget(budgets=(0.01, 0.05, 0.2), max_depth=14, scenarios=None):
    scenarios = (scenarios or make_scenarios())[:6]
    rows = []
    for b in budgets:
        for name in CONFIG_NAMES:
            ab, heur = SearchAgent.CONFIGS[name]
            depths = []
            for _, s in scenarios:
                _, st = Searcher(max_depth, ab, heur).search(s, time_limit=b)
                depths.append(st.depth)
            rows.append({"time_budget_s": b, "config": name,
                         "avg_depth_reached": round(statistics.mean(depths), 2)})
            print(f"budget={b:<5} {name:<32} depth={rows[-1]['avg_depth_reached']}")
    return rows


# ------------------------------------------------------------------------- Exp C
def play_match(agent_max, agent_min, state, max_cycles=150):
    """Plays one game. Returns (+1 MAX wins / -1 MIN wins / 0 draw, cycles)."""
    s = state
    while not s.is_terminal() and s.cycle < max_cycles:
        agent = agent_max if s.to_move == MAX_PLAYER else agent_min
        s = s.apply(agent.choose_action(s))
    if not s.is_terminal():
        return 0, s.cycle
    u = s.utility()
    return (u > 0) - (u < 0), s.cycle


def openings(count=3, seed=11):
    """Random openings after 1-3 cycles; both sides are played from each."""
    rng = random.Random(seed)
    out = [GameState.initial()]
    while len(out) < count:
        s = GameState.initial()
        for _ in range(2 * rng.randint(1, 3)):
            s = s.apply(rng.choice(s.legal_actions()))
        out.append(s)
    return out # đã check


def experiment_matches(depth=4, n_openings=3):
    rows = []
    ops = openings(n_openings)
    for a in CONFIG_NAMES:
        for b in CONFIG_NAMES:
            if a == b:
                continue
            w = l = dr = 0
            cycles = []
            for op in ops:
                r, c = play_match(SearchAgent(a, depth), SearchAgent(b, depth), op)
                w += r == 1
                l += r == -1
                dr += r == 0
                cycles.append(c)
            rows.append({"MAX_agent": a, "MIN_agent": b, "MAX_wins": w,
                         "MIN_wins": l, "draws": dr,
                         "avg_cycles": round(statistics.mean(cycles), 1)})
            print(f"{a:<32} (MAX) vs {b:<32} (MIN): {w}-{l}-{dr}")
    return rows #đã check


if __name__ == "__main__":
    t0 = time.perf_counter()
    print("=== Exp A: computational cost ===")
    write_csv("results_cost.csv", experiment_cost())
    print("\n=== Exp B: depth reached under a time budget ===")
    write_csv("results_depth_budget.csv", experiment_depth_budget())
    print("\n=== Exp C: round-robin matches (depth 4) ===")
    write_csv("results_matches.csv", experiment_matches())
    print(f"\nTotal: {time.perf_counter() - t0:.1f}s")