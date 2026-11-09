"""Task 1 - Requirement 1: N-Queens as a Propositional Logic problem.

Classes
-------
Board               : maps square (row, col) <-> propositional variable id.
CNFFormula          : container of CNF clauses (list of int lists, DIMACS style).
ConstraintGenerator : discovers attack constraints and converts them to CNF.
"""
from itertools import combinations
from math import comb


class Board:
    """N x N board. Square (r, c) <-> variable id = r*N + c + 1 (PySAT needs ids >= 1)."""

    #hàm khởi tạo
    def __init__(self, n: int):
        if n < 1:
            raise ValueError("N must be >= 1")
        self.n = n

    #chuyển tọa độ -> ID PySAT
    def var(self, r: int, c: int) -> int:
        return r * self.n + c + 1

    #chuyển ID PySAT -> Tọa độ
    def square(self, var: int) -> tuple:
        return divmod(var - 1, self.n)

    @property
    #tổng số biến
    def num_vars(self) -> int:
        return self.n * self.n

    #danh sách tất cả các ô
    def squares(self):
        return [(r, c) for r in range(self.n) for c in range(self.n)]

    #trích xuất vị trí quân Hậu từ lời giải của PySAT
    def model_to_queens(self, model):
        return sorted(self.square(v) for v in model if v > 0 and v <= self.num_vars)

    #trích xuất vị trí quân Hậu từ lời giải của PySAT
    def render(self, queens) -> str:
        q = set(queens)
        return "\n".join(
            " ".join("Q" if (r, c) in q else "." for c in range(self.n))
            for r in range(self.n)
        )


class CNFFormula:
    def __init__(self):
        self.clauses = []

    def add(self, clause):
        self.clauses.append(list(clause))

    def __len__(self):
        return len(self.clauses)

    def __iter__(self):
        return iter(self.clauses)

    def to_dimacs(self, num_vars: int) -> str:
        lines = [f"p cnf {num_vars} {len(self.clauses)}"]
        lines += [" ".join(map(str, cl)) + " 0" for cl in self.clauses]
        return "\n".join(lines)


class ConstraintGenerator:
    """Discovers the constraints of N-Queens and converts them to CNF."""

    def __init__(self, board: Board):
        self.board = board

    # ---- Step 1: constraint discovery -------------------------------------
    @staticmethod
    def attacks(a, b) -> bool:
        """Two distinct squares attack each other iff same row, column or diagonal."""
        (r1, c1), (r2, c2) = a, b
        return a != b and (r1 == r2 or c1 == c2 or abs(r1 - r2) == abs(c1 - c2))

    def attacking_pairs_naive(self):
        """O(N^4) pair scan: simple and obviously correct."""
        sq = self.board.squares()
        return [(a, b) for a, b in combinations(sq, 2) if self.attacks(a, b)]

    def attacking_pairs_grouped(self):
        """Optimised: group squares by line (row, col, i-j, i+j), pair within groups.
        Only generates pairs that truly attack (about O(N^3))."""
        groups = {}
        for r, c in self.board.squares():
            for key in (("row", r), ("col", c), ("d1", r - c), ("d2", r + c)):
                groups.setdefault(key, []).append((r, c))
        pairs = []
        for cells in groups.values():
            pairs.extend(combinations(cells, 2))
        return pairs

    # ---- Step 2: conversion to CNF ----------------------------------------
    def at_least_one_per_row(self):
        n, b = self.board.n, self.board
        return [[b.var(r, c) for c in range(n)] for r in range(n)]

    def at_most_one_clauses(self, pairs):
        """x(a) -> not x(b)  ==  (not x(a)) or (not x(b))."""
        b = self.board
        return [[-b.var(*p), -b.var(*q)] for p, q in pairs]

    def generate(self, optimized: bool = True) -> CNFFormula:
        cnf = CNFFormula()
        for cl in self.at_least_one_per_row():          # C1
            cnf.add(cl)
        pairs = self.attacking_pairs_grouped() if optimized else self.attacking_pairs_naive()
        for cl in self.at_most_one_clauses(pairs):      # C2-C5
            cnf.add(cl)
        return cnf

    @staticmethod
    def expected_clause_count(n: int) -> int:
        """N + 2N*C(N,2) + 4*C(N,3) + 2*C(N,2)"""
        return n + 2 * n * comb(n, 2) + 4 * comb(n, 3) + 2 * comb(n, 2)


if __name__ == "__main__":
    for n in (4, 5, 6, 8):
        gen = ConstraintGenerator(Board(n))
        a = gen.generate(optimized=False)
        b = gen.generate(optimized=True)
        print(f"N={n}: vars={n*n}, naive={len(a)}, grouped={len(b)}, "
              f"formula={gen.expected_clause_count(n)}")
