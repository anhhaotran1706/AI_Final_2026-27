"""Builds a Kakuro puzzle with a KNOWN solution from a white/black pattern (for testing)."""
import random

PATTERN_DEMO = ["######",
                "#WW#WW",
                "#WWWWW",
                "#WWWWW",
                "#WW#WW"]


def generate(pattern=PATTERN_DEMO, seed=1):
    rng = random.Random(seed)
    R, C = len(pattern), len(pattern[0])
    white = lambda r, c: 0 <= r < R and 0 <= c < C and pattern[r][c] == "W"
    sol = {}

    def ok(r, c, d):
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            rr, cc = r + dr, c + dc
            while white(rr, cc):
                if sol.get((rr, cc)) == d:
                    return False
                rr, cc = rr + dr, cc + dc
        return True

    cells = [(r, c) for r in range(R) for c in range(C) if white(r, c)]

    def fill(i):
        if i == len(cells):
            return True
        r, c = cells[i]
        ds = list(range(1, 10)); rng.shuffle(ds)
        for d in ds:
            if ok(r, c, d):
                sol[(r, c)] = d
                if fill(i + 1):
                    return True
                del sol[(r, c)]
        return False

    assert fill(0)

    def run_sum(r, c, dr, dc):
        s, rr, cc, n = 0, r + dr, c + dc, 0
        while white(rr, cc):
            s += sol[(rr, cc)]; rr += dr; cc += dc; n += 1
        return s if n else ""

    lines = []
    for r in range(R):
        toks = []
        for c in range(C):
            if white(r, c):
                toks.append(".")
            else:
                down, across = run_sum(r, c, 1, 0), run_sum(r, c, 0, 1)
                toks.append("#" if down == "" and across == "" else f"{down}\\{across}")
        lines.append(" ".join(toks))
    return "\n".join(lines), sol


def _runs_ok(g):
    """Every maximal white run must have length 2..9 (no single cells, no run > 9)."""
    R, C = len(g), len(g[0])
    for lines in ([[g[r][c] for c in range(C)] for r in range(R)],
                  [[g[r][c] for r in range(R)] for c in range(C)]):
        for line in lines:
            n = 0
            for ch in line + ["#"]:
                if ch == "W":
                    n += 1
                else:
                    if n == 1 or n > 9:
                        return False
                    n = 0
    return True


def _repair(g):
    """Blacken single-cell runs and split runs longer than 9 until the pattern is valid."""
    R, C = len(g), len(g[0])
    while not _runs_ok(g):
        for coords in ([[(r, c) for c in range(C)] for r in range(R)],
                       [[(r, c) for r in range(R)] for c in range(C)]):
            for line in coords:
                run = []
                for cell in line + [None]:
                    if cell is not None and g[cell[0]][cell[1]] == "W":
                        run.append(cell)
                        continue
                    if len(run) == 1:
                        g[run[0][0]][run[0][1]] = "#"
                    elif len(run) > 9:
                        m = run[len(run) // 2]
                        g[m[0]][m[1]] = "#"
                    run = []


def random_pattern(R, C, p=0.22, seed=0):
    """Random W/# pattern with black border row/column and valid run lengths (2..9)."""
    rng = random.Random(seed)
    g = [["#"] * C for _ in range(R)]
    for r in range(1, R):
        for c in range(1, C):
            g[r][c] = "#" if rng.random() < p else "W"
    _repair(g)
    return ["".join(row) for row in g]


if __name__ == "__main__":
    text, sol = generate()
    open("puzzles/demo_6x5.txt", "w").write(text + "\n")
    print(text)