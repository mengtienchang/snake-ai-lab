# -*- coding: utf-8 -*-
"""手寫尋路 vs 成熟第三方庫 —— 差分驗證與效能對比。

    .venv/bin/python compare_pathfind.py

兩件事：
  1. 差分測試：幾百個隨機棋盤上，手寫版和庫版必須給出同樣的答案
     （BFS 比路徑長度、Dijkstra 比路徑總代價；「到不了」也要一致）。
     成熟庫在這裡扮演「標準答案」，驗證手寫版沒寫錯。
  2. 效能：同樣的呼叫各跑 N 次計時。
"""

import random
import time

from environment.config import GRID_W, GRID_H
from algorithms.pathfind import bfs_path, dijkstra_path
from algorithms.pathfind_lib import lib_bfs_path, lib_dijkstra_path


def random_scenario(rng, block_density):
    """隨機障礙 + 不重疊的隨機起終點。"""
    cells = [(x, y) for x in range(GRID_W) for y in range(GRID_H)]
    blocked = set(rng.sample(cells, int(len(cells) * block_density)))
    free = [c for c in cells if c not in blocked]
    start, goal = rng.sample(free, 2)
    return start, goal, blocked


def make_cost_fn(rough):
    return lambda cell: 3 if cell in rough else 1


def main():
    rng = random.Random(2026)
    n_cases = 300

    # ---- 1. BFS 差分：路徑長度必須一致 ----
    mismatch = 0
    for _ in range(n_cases):
        start, goal, blocked = random_scenario(rng, rng.uniform(0, 0.35))
        ours = bfs_path(start, goal, blocked)
        theirs = lib_bfs_path(start, goal, blocked)
        if (ours is None) != (theirs is None):
            mismatch += 1
        elif ours is not None and len(ours) != len(theirs):
            mismatch += 1
    print("BFS      vs python-pathfinding：%d/%d 一致%s" % (
        n_cases - mismatch, n_cases, "　✓" if mismatch == 0 else "　✗ 有差異！"))

    # ---- 2. Dijkstra 差分：路徑總代價必須一致 ----
    mismatch = 0
    for _ in range(n_cases):
        start, goal, blocked = random_scenario(rng, rng.uniform(0, 0.3))
        cells = [(x, y) for x in range(GRID_W) for y in range(GRID_H)]
        rough = set(rng.sample(cells, int(len(cells) * 0.2)))
        cost = make_cost_fn(rough)
        ours = dijkstra_path(start, goal, blocked, cost)
        theirs = lib_dijkstra_path(start, goal, blocked, cost)
        if (ours is None) != (theirs is None):
            mismatch += 1
        elif ours is not None:
            c_ours = sum(cost(c) for c in ours[1:])
            c_theirs = sum(cost(c) for c in theirs[1:])
            if c_ours != c_theirs:
                mismatch += 1
    print("Dijkstra vs networkx          ：%d/%d 一致%s" % (
        n_cases - mismatch, n_cases, "　✓" if mismatch == 0 else "　✗ 有差異！"))

    # ---- 3. 效能：同一批場景各跑一輪 ----
    scenarios = [random_scenario(rng, 0.2) for _ in range(200)]
    rough = set(rng.sample([(x, y) for x in range(GRID_W)
                            for y in range(GRID_H)], 120))
    cost = make_cost_fn(rough)

    t0 = time.perf_counter()
    for s, g, b in scenarios:
        bfs_path(s, g, b)
    t_ours_bfs = time.perf_counter() - t0

    t0 = time.perf_counter()
    for s, g, b in scenarios:
        lib_bfs_path(s, g, b)
    t_lib_bfs = time.perf_counter() - t0

    t0 = time.perf_counter()
    for s, g, b in scenarios:
        dijkstra_path(s, g, b, cost)
    t_ours_dij = time.perf_counter() - t0

    t0 = time.perf_counter()
    for s, g, b in scenarios:
        lib_dijkstra_path(s, g, b, cost)
    t_lib_dij = time.perf_counter() - t0

    n = len(scenarios)
    print()
    print("效能（%d 次呼叫，%dx%d 棋盤、20%% 障礙）：" % (n, GRID_W, GRID_H))
    print("  BFS      手寫 %6.1f ms ｜ python-pathfinding %6.1f ms ｜ 手寫快 %.1f 倍"
          % (t_ours_bfs * 1000, t_lib_bfs * 1000, t_lib_bfs / t_ours_bfs))
    print("  Dijkstra 手寫 %6.1f ms ｜ networkx           %6.1f ms ｜ 手寫快 %.1f 倍"
          % (t_ours_dij * 1000, t_lib_dij * 1000, t_lib_dij / t_ours_dij))


if __name__ == "__main__":
    main()
