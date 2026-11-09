"""Task 1 - Requirement 3: N-Queens with Min-Conflicts + variable-selection heuristics.

State representation: one queen per column. rows[c] = row of the queen in column c.
Variable = column c, value = row r.  (Column constraints are satisfied by construction.)

Conflict counts are maintained incrementally with 3 counters, so that evaluating
the conflicts of a queen costs O(1):
    row_cnt[r], d1_cnt[r - c + N - 1], d2_cnt[r + c]
conflicts(c, r) = row_cnt[r] + d1_cnt[..] + d2_cnt[..]   (minus 3 if (c, r) is itself placed)
"""
import csv
import random
import statistics
import time
from abc import ABC, abstractmethod


# --------------------------------------------------------------------------- state
class QueensState:
    def __init__(self, n: int, rows):
        self.n = n
        self.rows = list(rows)
        self.row_cnt = [0] * n
        self.d1_cnt = [0] * (2 * n - 1)
        self.d2_cnt = [0] * (2 * n - 1)
        for c, r in enumerate(self.rows):
            self._add(c, r, +1)

    def _add(self, c, r, delta):
        self.row_cnt[r] += delta
        self.d1_cnt[r - c + self.n - 1] += delta
        self.d2_cnt[r + c] += delta

    def conflicts(self, c, r):
        k = (self.row_cnt[r] + self.d1_cnt[r - c + self.n - 1] + self.d2_cnt[r + c])
        if self.rows[c] == r:           # remove the queen's own contribution
            k -= 3
        return k

    def move(self, c, new_r):
        self._add(c, self.rows[c], -1)
        self.rows[c] = new_r
        self._add(c, new_r, +1)

    def conflicted_columns(self):
        return [c for c in range(self.n) if self.conflicts(c, self.rows[c]) > 0]

    def total_conflicts(self):
        return sum(self.conflicts(c, self.rows[c]) for c in range(self.n)) // 2


# ------------------------------------------------------------- variable selectors
class VariableSelector(ABC):
    name = "base"

    def reset(self, state):          # called at start of each run
        pass

    @abstractmethod
    def select(self, state, conflicted, rng):
        """Choose which conflicted column (variable) to repair."""


class RandomSelector(VariableSelector):
    """Standard Min-Conflicts: random conflicted variable."""
    name = "standard (random)"

    def select(self, state, conflicted, rng):
        return rng.choice(conflicted)


class MaxConflictSelector(VariableSelector):
    """Heuristic 1: the most-constrained / worst variable first (ties random)."""
    name = "max-conflict"

    def select(self, state, conflicted, rng):
        best = max(state.conflicts(c, state.rows[c]) for c in conflicted)
        return rng.choice([c for c in conflicted if state.conflicts(c, state.rows[c]) == best])


class MaxConflictTabuSelector(VariableSelector):
    """Heuristic 2: max-conflict, but a variable just repaired is tabu for `tenure`
    steps. This avoids the cycling that pure greedy selection falls into."""
    name = "max-conflict + tabu"

    def __init__(self, tenure=3):
        self.tenure = tenure
        self.tabu_until = {}
        self.step = 0

    def reset(self, state):
        self.tabu_until = {}
        self.step = 0

    def select(self, state, conflicted, rng):
        self.step += 1
        allowed = [c for c in conflicted if self.tabu_until.get(c, 0) <= self.step] or conflicted
        best = max(state.conflicts(c, state.rows[c]) for c in allowed)
        pick = rng.choice([c for c in allowed if state.conflicts(c, state.rows[c]) == best])
        self.tabu_until[pick] = self.step + self.tenure
        return pick


# -------------------------------------------------------------------------- solver
class MinConflictsSolver:
    def __init__(self, n, selector: VariableSelector, max_steps=None, seed=None):
        self.n = n
        self.selector = selector
        self.max_steps = max_steps if max_steps is not None else 50 * n
        self.rng = random.Random(seed)

    def random_initial(self):
        return QueensState(self.n, [self.rng.randrange(self.n) for i in range(self.n)])

    def best_value(self, state, c):
        vals = [state.conflicts(c, r) for r in range(self.n)]
        m = min(vals)
        return self.rng.choice([r for r, v in enumerate(vals) if v == m])

    def solve(self, initial_state=None):
        """Returns (solved, state, steps, seconds)."""
        state = initial_state or self.random_initial()
        self.selector.reset(state)
        t0 = time.perf_counter()
        for step in range(self.max_steps + 1):
            conflicted = state.conflicted_columns()
            if not conflicted:
                return True, state, step, time.perf_counter() - t0
            c = self.selector.select(state, conflicted, self.rng)
            state.move(c, self.best_value(state, c))
        return False, state, self.max_steps, time.perf_counter() - t0


# ----------------------------------------------------------------------- experiments
class Experiment:
    def __init__(self, sizes, trials=30, selectors=None):
        self.sizes = sizes
        self.trials = trials
        self.selectors = selectors or [RandomSelector, MaxConflictSelector,
                                       MaxConflictTabuSelector]
        self.rows = []

    def run(self):
        for n in self.sizes:
            for sel_cls in self.selectors:
                steps, times, ok = [], [], 0
                for t in range(self.trials):
                    seed = 1000 * n + t                    # same seed => same initial state
                    solver = MinConflictsSolver(n, sel_cls(), seed=seed)
                    init = solver.random_initial()
                    solved, _, s, sec = solver.solve(init)
                    ok += solved
                    steps.append(s)
                    times.append(sec)
                row = {"N": n, "selector": sel_cls.name,
                       "success_rate": ok / self.trials,
                       "avg_steps": round(statistics.mean(steps), 1),
                       "avg_time_s": round(statistics.mean(times), 5)}
                self.rows.append(row)
                print(f"N={n:<5} {row['selector']:<22} success={row['success_rate']:.2f} "
                      f"steps={row['avg_steps']:<8} time={row['avg_time_s']}")
        return self.rows

    def save_csv(self, path="results_minconflicts.csv"):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.rows[0].keys()))
            w.writeheader()
            w.writerows(self.rows)


if __name__ == "__main__":
    s = MinConflictsSolver(8, MaxConflictTabuSelector(), seed=1)
    solved, st, steps, sec = s.solve()
    print("N=8 solved:", solved, "steps:", steps, "rows:", st.rows)
    exp = Experiment([8, 16, 32, 64, 128, 256], trials=30)
    exp.run()