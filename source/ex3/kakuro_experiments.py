"""Task 3 - Requirement 2: evaluation of the Kakuro solver on the complex 9x9 board.

  A  Correctness   : independent verification of the solution + uniqueness check
  B  Effectiveness : ablation of the techniques (nodes, backtracks, time)
  C  Stability     : 30 randomised runs (tie-breaking / value order) on the same board
  D  Scaling       : generated boards of growing size, with and without restarts

Usage:  python kakuro_experiments.py [A] [B] [C] [D]      (default: A B C)
"""
import csv
import re
import statistics
import sys
import time

from kakuro_csp import KakuroCSP, KakuroPuzzle
from kakuro_solver import KakuroSolver

BOARD = "puzzles/complex_9x9.txt"

CONFIGS = [   # name, prune_domains, solver switches
    ("1. Backtracking (static order)", False, dict(propagation=False, mrv=False, degree=False, lcv=False)),
    ("2. + domain pruning by combinations", True, dict(propagation=False, mrv=False, degree=False, lcv=False)),
    ("3. + MRV + Degree", True, dict(propagation=False, mrv=True, degree=True, lcv=False)),
    ("4. Propagation (static order)", True, dict(propagation=True, mrv=False, degree=False, lcv=False)),
    ("5. Propagation + MRV + Degree", True, dict(propagation=True, mrv=True, degree=True, lcv=False)),
    ("6. Propagation + MRV + Degree + LCV", True, dict(propagation=True, mrv=True, degree=True, lcv=True)),
]


def load(path=BOARD):
    return open(path).read()


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------------ A
def verify_independent(text, solution):
    """Re-checks the solution straight from the board text (does not use the CSP classes)."""
    grid = [l.split() for l in text.strip().splitlines()]
    R, C = len(grid), len(grid[0])
    for (r, c), d in solution.items():
        assert grid[r][c] == "." and 1 <= d <= 9
    assert sum(t == "." for row in grid for t in row) == len(solution)
    checked = 0
    for r in range(R):
        for c in range(C):
            m = re.match(r"^(\d*)\\(\d*)$", grid[r][c])
            if not m:
                continue
            for total, (dr, dc) in ((m.group(1), (1, 0)), (m.group(2), (0, 1))):
                if not total:
                    continue
                vals, rr, cc = [], r + dr, c + dc
                while 0 <= rr < R and 0 <= cc < C and grid[rr][cc] == ".":
                    vals.append(solution[(rr, cc)])
                    rr, cc = rr + dr, cc + dc
                if sum(vals) != int(total) or len(set(vals)) != len(vals) or not vals:
                    return False
                checked += 1
    return checked


def experiment_correctness():
    text = load()
    csp = KakuroCSP(KakuroPuzzle.from_text(text))
    solver = KakuroSolver(csp)
    sol = solver.solve()
    n_checked = verify_independent(text, sol)
    n_sol = KakuroSolver(csp).count_solutions(limit=2)
    print(csp.puzzle.render(sol))
    print(f"\nvariables={len(csp.variables)}  runs={len(csp.runs)}")
    print(f"independent check: all {n_checked} clues satisfied = {bool(n_checked)}")
    print(f"number of solutions (counted up to 2): {n_sol}  -> unique = {n_sol == 1}")
    sols = set()
    for name, prune, kw in CONFIGS:
        c2 = KakuroCSP(KakuroPuzzle.from_text(text), prune_domains=prune)
        s2 = KakuroSolver(c2, node_limit=30000, **kw).solve()
        if s2:
            sols.add(tuple(sorted(s2.items())))
            assert verify_independent(text, s2)
    print(f"configurations that finished within the limit return identical solutions: {len(sols) == 1}")
    return sol


# ------------------------------------------------------------------------ B
def experiment_ablation(node_limit=30000, repeats=5):
    text, rows = load(), []
    for name, prune, kw in CONFIGS:
        csp = KakuroCSP(KakuroPuzzle.from_text(text), prune_domains=prune)
        times = []
        for _ in range(repeats):
            s = KakuroSolver(csp, node_limit=node_limit, **kw)
            sol = s.solve()
            times.append(s.stats.seconds)
        st = s.stats
        rows.append({"configuration": name, "solved": bool(sol), "hit_node_limit": st.hit_limit,
                     "nodes": st.nodes, "backtracks": st.backtracks, "revisions": st.revisions,
                     "median_time_s": round(statistics.median(times), 5)})
        print(f"{name:<40} solved={rows[-1]['solved']!s:<5} nodes={st.nodes:<7} "
              f"backtracks={st.backtracks:<6} revisions={st.revisions:<6} "
              f"time={rows[-1]['median_time_s']}s" + ("  (node limit)" if st.hit_limit else ""))
    write_csv("results_ablation.csv", rows)
    return rows


# ------------------------------------------------------------------------ C
def experiment_stability(runs=30):
    text = load()
    csp = KakuroCSP(KakuroPuzzle.from_text(text))
    nodes, times, ok, sols = [], [], 0, set()
    for seed in range(runs):
        s = KakuroSolver(csp, seed=seed, node_limit=200000)
        sol = s.solve()
        if sol and verify_independent(text, sol):
            ok += 1
            sols.add(tuple(sorted(sol.items())))
        nodes.append(s.stats.nodes)
        times.append(s.stats.seconds)
    row = {"runs": runs, "success_rate": ok / runs, "distinct_solutions": len(sols),
           "nodes_mean": round(statistics.mean(nodes), 1), "nodes_std": round(statistics.pstdev(nodes), 1),
           "nodes_max": max(nodes), "time_mean_s": round(statistics.mean(times), 5),
           "time_std_s": round(statistics.pstdev(times), 5), "time_max_s": round(max(times), 5)}
    print(row)
    write_csv("results_stability.csv", [row])
    return row


# ------------------------------------------------------------------------ D
def experiment_scaling(sizes=(8, 10, 12, 14), boards_per_size=3):
    from generate_puzzle import generate, random_pattern
    rows = []
    for n in sizes:
        for k in range(boards_per_size):
            seed = 10 * n + k
            text, _ = generate(random_pattern(n, n, seed=seed), seed=seed)
            csp = KakuroCSP(KakuroPuzzle.from_text(text))
            a = KakuroSolver(csp, node_limit=20000)
            sa = a.solve()
            b = KakuroSolver(csp)
            sb = b.solve_with_restarts(max_total_nodes=300000)
            rows.append({"size": f"{n}x{n}", "seed": seed, "variables": len(csp.variables),
                         "plain_solved": bool(sa), "plain_nodes": a.stats.nodes,
                         "plain_time_s": round(a.stats.seconds, 3),
                         "restart_solved": bool(sb), "restart_nodes": b.stats.nodes,
                         "restarts": b.stats.restarts, "restart_time_s": round(b.stats.seconds, 3)})
            print(rows[-1], flush=True)
    write_csv("results_scaling.csv", rows)
    return rows


if __name__ == "__main__":
    which = [a.upper() for a in sys.argv[1:]] or ["A", "B", "C"]
    t0 = time.perf_counter()
    if "A" in which:
        print("=== A: correctness ===")
        experiment_correctness()
    if "B" in which:
        print("\n=== B: ablation on the complex board ===")
        experiment_ablation()
    if "C" in which:
        print("\n=== C: stability (30 randomised runs) ===")
        experiment_stability()
    if "D" in which:
        print("\n=== D: scaling on generated boards ===")
        experiment_scaling()
    print(f"\nTotal {time.perf_counter() - t0:.1f}s")