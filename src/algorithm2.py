# algorithm2.py - backtracking solver that has animation support.

import time
from copy import deepcopy


def cage_valid_partial(board, cage, n): #check function for checking cage valid or not
    cells, target, op = cage
    vals = []
    unfilled = 0

    for (r, c) in cells:
        if board[r][c] == 0:
            unfilled += 1
        vals.append(board[r][c])

    assigned = [v for v in vals if v != 0]

    if op == '=' or op == '':
        if len(assigned) == 0:
            return True
        return assigned[0] == target

    if op == '+':
        s = sum(assigned)
        if s > target:
            return False
        if unfilled == 0 and s != target:
            return False
        return True

    if op == '*':
        prod = 1
        for v in assigned:
            prod *= v
        if prod > target:
            return False
        if unfilled == 0 and prod != target:
            return False
        return True

    if op == '-':
        if len(assigned) < 2:
            return True
        a, b = assigned
        return abs(a - b) == target

    if op == '/':
        if len(assigned) < 2:
            return True
        a, b = assigned
        if min(a, b) == 0:
            return False
        return max(a, b) / min(a, b) == target

    return True


def backtracking_solve(cages, n): # backtracking solve loop

    board = [[0]*n for _ in range(n)]
    cells = [(r, c) for r in range(n) for c in range(n)]
    steps = 0
    start = time.time()

    def solve_cell(idx): #inner recursive function
        nonlocal steps
        if idx == n*n:
            return True

        r, c = cells[idx]

        for v in range(1, n+1):
            if v in board[r]:
                continue
            if any(board[x][c] == v for x in range(n)):
                continue

            board[r][c] = v
            steps += 1

            ok = True
            for cage in cages:
                if (r, c) in cage[0]:
                    if not cage_valid_partial(board, cage, n):
                        ok = False
                        break

            if ok and solve_cell(idx + 1):
                return True

            board[r][c] = 0

        return False

    solved = solve_cell(0)
    end = time.time()

    if solved:
        return deepcopy(board), steps, (end - start)
    else:
        return None, steps, (end - start)


class AnimatedBacktrackingSolver: #animated backtracking same function but records steps
    def __init__(self, cages, n):
        self.cages = cages
        self.n = n
        self.board = [[0]*n for _ in range(n)]
        self.steps = 0
        self.actions = []  

    def row_ok(self, r, v):
        return v not in self.board[r]

    def col_ok(self, c, v):
        return all(self.board[x][c] != v for x in range(self.n))

    def cage_ok(self, r, c):
        for cage in self.cages:
            if (r, c) in cage[0]:
                if not cage_valid_partial(self.board, cage, self.n):
                    return False
        return True

    def solve(self, idx=0):
        if idx == self.n * self.n:
            return True

        r = idx // self.n
        c = idx % self.n

        for v in range(1, self.n+1):
            if not self.row_ok(r, v):
                continue
            if not self.col_ok(c, v):
                continue

            self.board[r][c] = v
            self.steps += 1
            self.actions.append((r, c, v, True))

            if not self.cage_ok(r, c):
                self.board[r][c] = 0
                self.actions.append((r, c, 0, False))
                continue

            if self.solve(idx + 1):
                return True

            self.board[r][c] = 0
            self.actions.append((r, c, 0, False))

        return False


def compute_animation_sequence(cages, n):
    solver = AnimatedBacktrackingSolver(cages, n)
    start = time.time()
    solver.solve()
    end = time.time()
    return deepcopy(solver.board), solver.steps, (end - start), solver.actions[:]
