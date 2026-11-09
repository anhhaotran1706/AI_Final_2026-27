"""Task 1 - Requirement 2: solve N-Queens with Glucose3 (PySAT) and run experiments.

Install:  pip install python-sat
Run:      python nqueens_sat.py
"""
import csv
import time

from pysat.solvers import Glucose3
from source.ex1.nqueens_cnf import Board, ConstraintGenerator

class SATQueensSolver:
    """Builds the CNF for N-Queens and solves it with Glucose3."""

    def __init__(self, n: int):
        self.n = n
        self.board = Board(n)
        self.generator = ConstraintGenerator(self.board)
        self.cnf = None
        self.gen_time = 0.0
        self.solve_time = 0.0

    def build(self):
        t0 = time.perf_counter()
        self.cnf = self.generator.generate(optimized=True)
        self.gen_time = time.perf_counter() - t0
        return self.cnf

    def solve(self):
        """Return list of (row, col) queens, or None if UNSAT."""
        if self.cnf is None:
            self.build()
        with Glucose3(bootstrap_with=self.cnf.clauses) as solver:
            t0 = time.perf_counter()
            sat = solver.solve()
            self.solve_time = time.perf_counter() - t0   # only the solver call
            model = solver.get_model() if sat else None
        return self.board.model_to_queens(model) if sat else None

    @staticmethod
    def is_valid(queens, n) -> bool:
        """Independent verification of a solution (does not use the CNF)."""
        if len(queens) != n:
            return False
        for i in range(n):
            for j in range(i + 1, n):
                if ConstraintGenerator.attacks(queens[i], queens[j]):
                    return False
        return True


class ExperimentRunner:
    def __init__(self, sizes):
        self.sizes = sizes
        self.results = []

    def run(self, time_limit=60.0):
        for n in self.sizes:
            s = SATQueensSolver(n)
            s.build()
            queens = s.solve()
            row = {
                "N": n,
                "variables": n * n,
                "clauses": len(s.cnf),
                "gen_time_s": round(s.gen_time, 5),
                "solve_time_s": round(s.solve_time, 5),
                "valid": bool(queens) and SATQueensSolver.is_valid(queens, n),
            }
            self.results.append(row)
            print(f"N={n:<4} vars={row['variables']:<7} clauses={row['clauses']:<9} "
                  f"gen={row['gen_time_s']:<9} solve={row['solve_time_s']:<9} valid={row['valid']}")
            if s.gen_time + s.solve_time > time_limit:
                print("Time limit exceeded, stopping.")
                break
        return self.results

    def save_csv(self, path="results_sat.csv"):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.results[0].keys()))
            w.writeheader()
            w.writerows(self.results)

    def plot(self, path="results_sat.png"):
        import matplotlib.pyplot as plt
        ns = [r["N"] for r in self.results]
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        ax[0].plot(ns, [r["clauses"] for r in self.results], "o-")
        ax[0].set_xlabel("N"); ax[0].set_ylabel("#clauses"); ax[0].set_title("CNF size")
        ax[1].plot(ns, [r["solve_time_s"] for r in self.results], "o-", label="solve")
        ax[1].plot(ns, [r["gen_time_s"] for r in self.results], "s--", label="generate")
        ax[1].set_xlabel("N"); ax[1].set_ylabel("seconds"); ax[1].legend()
        ax[1].set_title("Running time")
        plt.tight_layout(); plt.savefig(path, dpi=150)


if __name__ == "__main__":
    # Show one concrete solution
    demo = SATQueensSolver(8)
    q = demo.solve()
    print(demo.board.render(q), "\n")

    runner = ExperimentRunner([4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 40, 50, 60, 80, 100])
    runner.run()
    runner.save_csv()
    try:
        runner.plot()
    except ImportError:
        print("matplotlib not installed, skip plot")