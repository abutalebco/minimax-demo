"""Tic-tac-toe engine with Minimax and Alpha-Beta pruning.

Convention: X is MAX, O is MIN.  Utility: +1 X wins, 0 draw, -1 O wins.
A board is a tuple of 9 cells: "X", "O" or " " (index 0..8, row by row).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

EMPTY = " "
LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
MOVE_ORDER = (4, 0, 2, 6, 8, 1, 3, 5, 7)  # centre, corners, edges: good ordering helps pruning
INF = math.inf


# ---------------------------------------------------------------- game rules
def other(p: str) -> str:
    return "O" if p == "X" else "X"


def turn_of(b: tuple) -> str:
    """Whose turn it is, assuming X always starts."""
    return "X" if b.count("X") == b.count("O") else "O"


def winner(b: tuple):
    for a, c, d in LINES:
        if b[a] != EMPTY and b[a] == b[c] == b[d]:
            return b[a]
    return None


def is_terminal(b: tuple) -> bool:
    return winner(b) is not None or EMPTY not in b


def utility(b: tuple) -> int:
    w = winner(b)
    return 1 if w == "X" else -1 if w == "O" else 0


def legal_moves(b: tuple) -> list:
    return [i for i in MOVE_ORDER if b[i] == EMPTY]


def play(b: tuple, i: int, p: str) -> tuple:
    return b[:i] + (p,) + b[i + 1:]


# ---------------------------------------------------------------- algorithms
@dataclass
class Stats:
    nodes: int = 0


def minimax(b, turn, st: Stats) -> int:
    st.nodes += 1
    if is_terminal(b):
        return utility(b)
    if turn == "X":  # MAX
        return max(minimax(play(b, m, "X"), "O", st) for m in legal_moves(b))
    return min(minimax(play(b, m, "O"), "X", st) for m in legal_moves(b))  # MIN


def alphabeta(b, turn, alpha, beta, st: Stats) -> int:
    st.nodes += 1
    if is_terminal(b):
        return utility(b)
    if turn == "X":
        v = -INF
        for m in legal_moves(b):
            v = max(v, alphabeta(play(b, m, "X"), "O", alpha, beta, st))
            alpha = max(alpha, v)
            if alpha >= beta:  # MIN above will never allow this branch
                break
        return v
    v = INF
    for m in legal_moves(b):
        v = min(v, alphabeta(play(b, m, "O"), "X", alpha, beta, st))
        beta = min(beta, v)
        if alpha >= beta:  # MAX above will never allow this branch
            break
    return v


@dataclass
class SearchResult:
    move: int
    value: int
    nodes: int


def search(b: tuple, turn: str, algo: str = "alphabeta") -> SearchResult:
    """Pick the best move for `turn`. algo: 'minimax' or 'alphabeta'."""
    st = Stats(nodes=1)  # count the root
    maxi = turn == "X"
    best_m, best_v = None, (-INF if maxi else INF)
    alpha, beta = -INF, INF
    for m in legal_moves(b):
        child = play(b, m, turn)
        if algo == "minimax":
            v = minimax(child, other(turn), st)
        else:
            v = alphabeta(child, other(turn), alpha, beta, st)
        if (maxi and v > best_v) or (not maxi and v < best_v):
            best_m, best_v = m, v
        if algo == "alphabeta":
            alpha, beta = (max(alpha, best_v), beta) if maxi else (alpha, min(beta, best_v))
    return SearchResult(best_m, int(best_v), st.nodes)


@lru_cache(maxsize=None)
def solve(b: tuple, turn: str) -> int:
    """Exact minimax value (memoised; used for fast move-value hints)."""
    if is_terminal(b):
        return utility(b)
    vals = [solve(play(b, m, turn), other(turn)) for m in legal_moves(b)]
    return max(vals) if turn == "X" else min(vals)


def move_values(b: tuple, turn: str) -> dict:
    """Exact value (X's perspective) of every legal move."""
    return {m: solve(play(b, m, turn), other(turn)) for m in legal_moves(b)}


# ---------------------------------------------------------------- tracing
class TraceTooLarge(Exception):
    pass


def trace_search(b: tuple, turn: str, algo: str, cap: int = 1600) -> list:
    """Record every step of the search as a list of event dicts (for the visualizer)."""
    events: list = []
    counter = [0]

    def add(e):
        if len(events) >= cap:
            raise TraceTooLarge
        events.append(e)

    def rec(board, t, parent, move, alpha, beta):
        nid = counter[0]
        counter[0] += 1
        add(dict(type="enter", id=nid, parent=parent, move=move, board=board, turn=t, alpha=alpha, beta=beta))
        if is_terminal(board):
            v = utility(board)
            add(dict(type="leaf", id=nid, value=v))
            return v
        maxi = t == "X"
        best = -INF if maxi else INF
        moves = legal_moves(board)
        for idx, m in enumerate(moves):
            v = rec(play(board, m, t), other(t), nid, m, alpha, beta)
            if maxi:
                best = max(best, v)
                alpha = max(alpha, best) if alpha is not None else None
            else:
                best = min(best, v)
                beta = min(beta, best) if beta is not None else None
            if alpha is not None and alpha >= beta:
                rest = tuple(moves[idx + 1:])
                if rest:
                    add(dict(type="prune", id=nid, moves=rest, alpha=alpha, beta=beta, turn=t))
                break
        add(dict(type="exit", id=nid, value=int(best), turn=t))
        return int(best)

    if algo == "alphabeta":
        rec(b, turn, None, None, -INF, INF)
    else:
        rec(b, turn, None, None, None, None)
    return events


if __name__ == "__main__":
    import time
    empty = (EMPTY,) * 9
    for algo in ("minimax", "alphabeta"):
        t0 = time.perf_counter()
        r = search(empty, "X", algo)
        print(f"{algo:10s} move={r.move} value={r.value} nodes={r.nodes:,} ({time.perf_counter() - t0:.2f}s)")
