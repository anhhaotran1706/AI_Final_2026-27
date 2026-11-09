"""Task 3 - Requirement 3 (logic part): records what the solver does, step by step.

The solver reports events through its `observer` hook; TraceRecorder turns them into a list
of TraceStep objects. Every step carries a full snapshot of the variable DOMAINS, so the UI
can show (and step backwards through) the domains, the constraint propagation and the
backtracking search without re-running anything.

Step kinds
    init       initial domains (after pruning by digit combinations)
    assign     search decision: variable := value
    revise     constraint propagation on one run narrowed some domains
    conflict   propagation emptied a domain -> the branch fails
    backtrack  the value failed, the search returns to the previous state
    solution   a complete valid assignment was found
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from kakuro_csp import Cell, KakuroCSP, KakuroPuzzle
from kakuro_solver import KakuroSolver, SolverStats

PRESETS = {
    "Full: propagation + MRV + Degree + LCV": dict(propagation=True, mrv=True, degree=True, lcv=True),
    "Propagation, static variable order": dict(propagation=True, mrv=False, degree=False, lcv=False),
    "Backtracking only (no propagation)": dict(propagation=False, mrv=False, degree=False, lcv=False),
}


@dataclass
class TraceStep:
    kind: str
    text: str
    domains: Dict[Cell, frozenset]
    assigned: Dict[Cell, int]
    changed: Set[Cell] = field(default_factory=set)
    focus: List[Cell] = field(default_factory=list)
    depth: int = -1
    assigns: int = 0
    backtracks: int = 0
    revisions: int = 0
    conflicts: int = 0


class TraceFull(Exception):
    """Raised by the recorder to stop the solver when max_steps is reached."""


class TraceRecorder:
    def __init__(self, csp: KakuroCSP, max_steps: int = 20000):
        self.csp = csp
        self.max_steps = max_steps
        self.steps: List[TraceStep] = []
        self.truncated = False
        self.assigned: Dict[Cell, int] = {}
        self.cur = {v: frozenset(d) for v, d in csp.domains.items()}
        self.states = {-1: dict(self.cur)}           # depth -> domains after propagation
        self.counts = dict(assigns=0, backtracks=0, revisions=0, conflicts=0)
        self._add("init", "Initial domains (digits that occur in some valid combination of every run)")

    # ----------------------------------------------------------------- helpers
    def _add(self, kind, text, changed=(), focus=(), depth=-1):
        if len(self.steps) >= self.max_steps:
            self.truncated = True
            raise TraceFull
        self.steps.append(TraceStep(kind, text, dict(self.cur), dict(self.assigned),
                                    set(changed), list(focus), depth, **self.counts))

    @staticmethod
    def _run_name(run):
        return f"{run.direction} run, sum {run.total}, {run.length} cells"

    def _base(self, depth):
        base = dict(self.states.get(depth - 1, self.states[-1]))
        for v, val in self.assigned.items():          # keep decisions visible in every mode
            base[v] = frozenset([val])
        return base

    # --------------------------------------------------------------- observer
    def observe(self, event, **d):
        if event == "assign":
            self.counts["assigns"] += 1
            self.assigned[d["var"]] = d["value"]
            self.cur = self._base(d["depth"])
            self.cur[d["var"]] = frozenset([d["value"]])
            self._add("assign", f"Depth {d['depth']}: assign cell {d['var']} = {d['value']}",
                      changed=[d["var"]], depth=d["depth"])
        elif event == "revise":
            self.counts["revisions"] += 1
            self.cur = dict(d["domains"])
            n = len(d["changed"])
            self._add("revise", f"Propagation on {self._run_name(d['run'])}: "
                                f"{n} cell{'s' if n > 1 else ''} narrowed",
                      changed=d["changed"], focus=d["run"].cells)
        elif event == "conflict":
            self.counts["conflicts"] += 1
            self._add("conflict", f"Conflict in {self._run_name(d['run'])}: a domain became empty",
                      focus=d["run"].cells)
        elif event == "propagate":
            self.states[d["depth"]] = dict(d["domains"])
            self.cur = dict(d["domains"])
        elif event == "backtrack":
            self.counts["backtracks"] += 1
            self.assigned.pop(d["var"], None)
            self.cur = self._base(d["depth"])
            self._add("backtrack", f"Backtrack: value {d['value']} of cell {d['var']} fails, undo",
                      changed=[d["var"]], depth=d["depth"])
        elif event == "solution":
            self.cur = {v: frozenset([x]) for v, x in d["solution"].items()}
            self._add("solution", "Solution found: every run satisfied")


def build_trace(puzzle_text: str, preset: str = None, max_steps: int = 20000, seed=None):
    """Runs the solver with a recorder. Returns (csp, steps, solution, stats, truncated)."""
    preset = preset or next(iter(PRESETS))
    csp = KakuroCSP(KakuroPuzzle.from_text(puzzle_text))
    rec = TraceRecorder(csp, max_steps)
    solver = KakuroSolver(csp, seed=seed, observer=rec.observe, **PRESETS[preset])
    try:
        solution = solver.solve()
        stats = solver.stats
    except TraceFull:
        solution, stats = None, solver.stats
    return csp, rec.steps, solution, stats, rec.truncated


if __name__ == "__main__":
    import sys
    text = open(sys.argv[1] if len(sys.argv) > 1 else "puzzles/complex_9x9.txt").read()
    for name in PRESETS:
        csp, steps, sol, st, trunc = build_trace(text, name)
        kinds = {}
        for s in steps:
            kinds[s.kind] = kinds.get(s.kind, 0) + 1
        print(f"{name}\n   steps={len(steps)} solved={bool(sol)} truncated={trunc} {kinds}")