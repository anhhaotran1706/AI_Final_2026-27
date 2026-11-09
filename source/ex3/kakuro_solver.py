"""Task 3 - Requirement 2: Kakuro solver = constraint propagation + Backtracking Search.

Constraint propagation (per run, repeated until a fixed point):
  1. ALL-DIFF   : when a cell has a single value, remove it from the other cells of the run.
  2. COMBINATIONS: keep only the digit sets {d1..dk} with sum = clue that can still be
                   assigned to the cells (bipartite matching between cells and digits with
                   respect to the current domains); every cell keeps only digits appearing
                   in at least one surviving combination.
  An emptied domain means the branch is inconsistent (failure).

Backtracking search heuristics (Lecture 08):
  * MRV     : choose the variable with the fewest remaining values
  * Degree  : tie-break by the number of unassigned neighbours (most constraining)
  * LCV     : try first the value that removes the fewest options from neighbours

Switches allow the ablation study done in kakuro_experiments.py.
`observer(event, **data)` is an optional hook used by the UI (requirement 3).
"""
import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from kakuro_csp import Cell, KakuroCSP, KakuroPuzzle, Run


@dataclass
class SolverStats:
    nodes: int = 0          # value assignments tried
    backtracks: int = 0     # variables whose all values failed
    revisions: int = 0      # run revisions in propagation
    seconds: float = 0.0
    solved: bool = False
    hit_limit: bool = False
    restarts: int = 0


class LimitReached(Exception):
    pass


class KakuroSolver:
    def __init__(self, csp: KakuroCSP, propagation: bool = True, mrv: bool = True,
                 degree: bool = True, lcv: bool = True, node_limit: Optional[int] = None,
                 seed: Optional[int] = None, observer: Optional[Callable] = None):
        self.csp = csp
        self.propagation, self.mrv, self.degree, self.lcv = propagation, mrv, degree, lcv
        self.node_limit = node_limit
        self.rng = random.Random(seed) if seed is not None else None
        self.observer = observer
        self.stats = SolverStats()

    def _emit(self, event, **data):
        if self.observer:
            self.observer(event, **data)

    # ================================================================ propagation
    @staticmethod
    def _combo_ok(cmb, cells, dom) -> bool:
        digits = set(cmb)
        for c in cells:
            if not (dom[c] & digits):
                return False
        match: Dict[int, Cell] = {}

        def augment(c, seen):
            for d in dom[c]:
                if d in digits and d not in seen:
                    seen.add(d)
                    if d not in match or augment(match[d], seen):
                        match[d] = c
                        return True
            return False

        return all(augment(c, set()) for c in cells)

    def _revise(self, run: Run, dom):
        """Make one run consistent. Returns the set of changed cells, or None on failure."""
        cells, changed = run.cells, set()
        while True:
            progress = False
            for c in cells:                                   # 1. all-different on singletons
                if len(dom[c]) == 1:
                    (d,) = dom[c]
                    for o in cells:
                        if o != c and d in dom[o]:
                            dom[o] = dom[o] - {d}
                            if not dom[o]:
                                return None
                            changed.add(o)
                            progress = True
            valid = [cb for cb in run.combos() if self._combo_ok(cb, cells, dom)]
            if not valid:                                     # 2. combination filtering
                return None
            union = set().union(*valid)
            for c in cells:
                nd = dom[c] & union
                if nd != dom[c]:
                    if not nd:
                        return None
                    dom[c] = nd
                    changed.add(c)
                    progress = True
            if not progress:
                return changed

    def _propagate(self, dom, runs) -> bool:
        queue = list(dict.fromkeys(runs))
        queued = set(queue)
        while queue:
            run = queue.pop()
            queued.discard(run)
            self.stats.revisions += 1
            changed = self._revise(run, dom)
            if changed is None:
                self._emit("conflict", run=run)
                return False
            if changed and self.observer:
                self._emit("revise", run=run, changed=set(changed), domains=dict(dom))
            for c in changed:
                for r in self.csp.runs_of[c]:
                    if r is not run and r not in queued:
                        queue.append(r)
                        queued.add(r)
        return True

    # ============================================================= variable/value choice
    def _tiebreak(self):
        return self.rng.random() if self.rng else 0

    def _degree(self, v, unassigned_set):
        return sum(1 for u in self.csp.neighbors[v] if u in unassigned_set)

    def _select(self, candidates, size_of, unassigned_set):
        if not self.mrv and not self.degree:
            return candidates[0]                              # static order
        def key(v):
            deg = self._degree(v, unassigned_set) if self.degree else 0
            return (size_of(v) if self.mrv else 0, -deg, self._tiebreak())
        return min(candidates, key=key)

    def _order_values(self, values, v, still_open):
        vals = sorted(values)
        if self.rng:
            self.rng.shuffle(vals)
        if self.lcv:                                          # fewest conflicts with neighbours
            nb = [u for u in self.csp.neighbors[v] if u in still_open]
            vals.sort(key=lambda d: sum(1 for u in nb if d in still_open[u]))
        return vals

    def _tick(self):
        self.stats.nodes += 1
        if self.node_limit and self.stats.nodes > self.node_limit:
            raise LimitReached

    # ================================================================ search: propagation
    def _search_prop(self, dom, depth):
        open_vars = [v for v in self.csp.variables if len(dom[v]) > 1]
        if not open_vars:
            yield {v: next(iter(dom[v])) for v in self.csp.variables}
            return
        open_set = set(open_vars)
        v = self._select(open_vars, lambda x: len(dom[x]), open_set)
        still = {u: dom[u] for u in open_vars}
        for d in self._order_values(dom[v], v, still):
            self._tick()
            nd = dict(dom)
            nd[v] = frozenset([d])
            self._emit("assign", var=v, value=d, depth=depth)
            if self._propagate(nd, self.csp.runs_of[v]):
                self._emit("propagate", domains=nd, depth=depth)
                yield from self._search_prop(nd, depth + 1)
            self._emit("backtrack", var=v, value=d, depth=depth)
        self.stats.backtracks += 1

    # ================================================================ search: plain
    def _search_plain(self, assign, depth):
        todo = [v for v in self.csp.variables if v not in assign]
        if not todo:
            yield dict(assign)
            return
        todo_set = set(todo)
        legal = lambda x: [d for d in self.csp.domains[x] if self.csp.consistent(x, d, assign)]
        v = self._select(todo, lambda x: len(legal(x)), todo_set) \
            if self.mrv else self._select(todo, None, todo_set)
        still = {u: set(self.csp.domains[u]) for u in todo}
        for d in self._order_values(legal(v), v, still):
            self._tick()
            assign[v] = d
            self._emit("assign", var=v, value=d, depth=depth)
            yield from self._search_plain(assign, depth + 1)
            del assign[v]
            self._emit("backtrack", var=v, value=d, depth=depth)
        self.stats.backtracks += 1

    # ================================================================ public API
    def _run(self):
        if not self.propagation:
            yield from self._search_plain({}, 0)
            return
        dom = {v: frozenset(d) for v, d in self.csp.domains.items()}
        if not self._propagate(dom, self.csp.runs):
            return
        self._emit("propagate", domains=dom, depth=-1)
        yield from self._search_prop(dom, 0)

    def solve(self):
        """Returns {cell: digit} or None. Statistics are in self.stats."""
        self.stats = SolverStats()
        t0 = time.perf_counter()
        sol = None
        try:
            sol = next(self._run(), None)
        except LimitReached:
            self.stats.hit_limit = True
        self.stats.seconds = time.perf_counter() - t0
        if sol is not None:
            assert self.csp.is_solution(sol), "solver returned an invalid solution"
            self.stats.solved = True
            self._emit("solution", solution=sol)
        return sol

    def solve_with_restarts(self, first_limit: int = 300, growth: float = 1.5,
                            max_total_nodes: Optional[int] = None, seed: int = 0):
        """Randomised restarts with a growing node limit. Search time on hard boards is
        heavy-tailed (a bad early choice can cost thousands of nodes); a short randomised
        run usually escapes it. Statistics are accumulated over all attempts."""
        saved = (self.node_limit, self.rng)
        total = SolverStats()
        t0 = time.perf_counter()
        limit, attempt, sol = first_limit, 0, None
        while True:
            self.rng = random.Random(seed + attempt)
            self.node_limit = limit
            self._emit("restart", attempt=attempt, node_limit=limit)
            sol = self.solve()
            st = self.stats
            total.nodes += st.nodes
            total.backtracks += st.backtracks
            total.revisions += st.revisions
            if sol is not None:
                total.solved = True
                break
            if not st.hit_limit:                  # tree exhausted: no solution exists
                break
            if max_total_nodes and total.nodes >= max_total_nodes:
                total.hit_limit = True
                break
            attempt += 1
            limit = int(limit * growth)
        total.restarts = attempt
        total.seconds = time.perf_counter() - t0
        self.stats = total
        self.node_limit, self.rng = saved
        return sol

    def count_solutions(self, limit: int = 2) -> int:
        """Counts solutions up to `limit` (limit=2 is enough to test uniqueness)."""
        self.stats = SolverStats()
        n = 0
        try:
            for _ in self._run():
                n += 1
                if n >= limit:
                    break
        except LimitReached:
            self.stats.hit_limit = True
        return n


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "puzzles/demo_6x5.txt"
    csp = KakuroCSP(KakuroPuzzle.from_text(open(path).read()))
    solver = KakuroSolver(csp)
    sol = solver.solve()
    print(csp.puzzle.render(sol) if sol else "No solution")
    print(solver.stats)
    print("unique solution:", KakuroSolver(csp).count_solutions(2) == 1)