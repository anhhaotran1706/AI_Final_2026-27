"""Task 3 - Requirement 1: Kakuro as a Constraint Satisfaction Problem.

Board text format (one row per line, tokens separated by spaces):
    .        white cell (to be filled with a digit 1..9)
    #        black cell without clue
    d\\r      clue cell: d = DOWN sum (lower-left number), r = ACROSS sum (upper-right number);
             either side may be empty, e.g.  16\\   or   \\23   or   16\\23

CSP formulation
    Variables   : one per white cell (row, col)
    Domains     : {1..9}, pruned at the start to the digits that occur in at least one
                  valid combination of every run containing the cell
    Constraints : for every run (maximal sequence of white cells right of / below a clue)
                    - ALL-DIFFERENT : the digits of the run are pairwise different
                    - SUM           : the digits of the run add up to the clue
"""
import re
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

Cell = Tuple[int, int]
DIGITS = range(1, 10)
CLUE_RE = re.compile(r"^(\d*)\\(\d*)$")


class Run:
    """One run = one clue = one group of constraints (all-different + sum)."""

    def __init__(self, direction: str, clue_cell: Cell, cells: List[Cell], total: int):
        self.direction = direction            # 'across' or 'down'
        self.clue_cell = clue_cell
        self.cells = cells
        self.total = total
        self._combos = None

    @property
    def length(self) -> int:
        return len(self.cells)

    def combos(self) -> List[Tuple[int, ...]]:
        """All sets of `length` distinct digits whose sum equals the clue."""
        if self._combos is None:
            self._combos = [c for c in combinations(DIGITS, self.length)
                            if sum(c) == self.total]
        return self._combos

    def allowed_digits(self) -> Set[int]:
        return {d for c in self.combos() for d in c}

    def consistent(self, assignment: Dict[Cell, int]) -> bool:
        """Partial check: no repeated digit, and the remaining cells can still reach the sum."""
        vals = [assignment[c] for c in self.cells if c in assignment]
        if len(set(vals)) < len(vals):
            return False
        k = self.length - len(vals)
        s = sum(vals)
        if k == 0:
            return s == self.total
        rest = [d for d in DIGITS if d not in vals]
        if len(rest) < k:
            return False
        return s + sum(rest[:k]) <= self.total <= s + sum(rest[-k:])

    def __repr__(self):
        return f"Run({self.direction}, clue@{self.clue_cell}, len={self.length}, sum={self.total})"


class KakuroPuzzle:
    """The board: grid of cells plus the extracted runs."""

    def __init__(self, grid: List[List[str]]):
        self.grid = grid
        self.rows, self.cols = len(grid), len(grid[0])
        self.white: List[Cell] = [(r, c) for r in range(self.rows) for c in range(self.cols)
                                  if grid[r][c] == "."]
        self.runs: List[Run] = self._extract_runs()

    @classmethod
    def from_text(cls, text: str) -> "KakuroPuzzle":
        grid = [line.split() for line in text.strip().splitlines() if line.strip()]
        if len({len(r) for r in grid}) != 1:
            raise ValueError("All rows must have the same number of cells")
        for row in grid:
            for tok in row:
                if tok not in (".", "#") and not CLUE_RE.match(tok):
                    raise ValueError(f"Bad cell token: {tok!r}")
        return cls(grid)

    def _extract_runs(self) -> List[Run]:
        runs = []
        for r in range(self.rows):
            for c in range(self.cols):
                m = CLUE_RE.match(self.grid[r][c])
                if not m:
                    continue
                down, across = m.group(1), m.group(2)
                if across:
                    runs.append(Run("across", (r, c), self._walk(r, c, 0, 1), int(across)))
                if down:
                    runs.append(Run("down", (r, c), self._walk(r, c, 1, 0), int(down)))
        return runs

    def _walk(self, r, c, dr, dc) -> List[Cell]:
        cells, r, c = [], r + dr, c + dc
        while 0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c] == ".":
            cells.append((r, c))
            r, c = r + dr, c + dc
        return cells

    def render(self, assignment: Optional[Dict[Cell, int]] = None) -> str:
        assignment = assignment or {}
        out = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                t = self.grid[r][c]
                if t == ".":
                    row.append(f"{assignment[(r, c)]:^7}" if (r, c) in assignment else f"{'.':^7}")
                elif t == "#":
                    row.append("#######")
                else:
                    row.append(f"{t:^7}")
            out.append("|".join(row))
        return "\n".join(out)


class KakuroCSP:
    """CSP view of a puzzle: variables, domains, constraints, neighbours."""

    def __init__(self, puzzle: KakuroPuzzle, prune_domains: bool = True):
        self.puzzle = puzzle
        self.variables: List[Cell] = list(puzzle.white)
        self.runs = puzzle.runs
        self.runs_of: Dict[Cell, List[Run]] = {v: [] for v in self.variables}
        for run in self.runs:
            for cell in run.cells:
                self.runs_of[cell].append(run)
        self.domains: Dict[Cell, Set[int]] = {}
        for v in self.variables:
            dom = set(DIGITS)
            if prune_domains:
                for run in self.runs_of[v]:
                    dom &= run.allowed_digits()
            self.domains[v] = dom
        self.neighbors: Dict[Cell, Set[Cell]] = {
            v: {u for run in self.runs_of[v] for u in run.cells if u != v}
            for v in self.variables}

    # ------------------------------------------------------------- constraints
    def consistent(self, var: Cell, value: int, assignment: Dict[Cell, int]) -> bool:
        """Would assigning var=value keep every constraint on var satisfiable?"""
        trial = dict(assignment)
        trial[var] = value
        return all(run.consistent(trial) for run in self.runs_of[var])

    def is_complete(self, assignment) -> bool:
        return all(v in assignment for v in self.variables)

    def is_solution(self, assignment: Dict[Cell, int]) -> bool:
        return (self.is_complete(assignment)
                and all(assignment[v] in self.domains[v] for v in self.variables)
                and all(run.consistent(assignment) for run in self.runs))

    # -------------------------------------------------------------- statistics
    def statistics(self) -> dict:
        n_pairs = sum(run.length * (run.length - 1) // 2 for run in self.runs)
        return {
            "variables": len(self.variables),
            "runs (= sum constraints)": len(self.runs),
            "all-different constraints": len(self.runs),
            "binary != pairs (if decomposed)": n_pairs,
            "avg initial domain size": round(
                sum(len(d) for d in self.domains.values()) / len(self.variables), 2),
            "avg domain size before pruning": 9.0,
        }


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "puzzles/demo_6x5.txt"
    csp = KakuroCSP(KakuroPuzzle.from_text(open(path).read()))
    print(csp.puzzle.render())
    for run in csp.runs:
        print(run, "combos:", run.combos())
    print(csp.statistics())