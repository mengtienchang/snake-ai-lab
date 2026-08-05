# -*- coding: utf-8 -*-
"""共用尋路工具：BFS、Dijkstra、A*、路徑代價、前向模擬。"""

import heapq
from collections import deque

from environment.config import (
    GRID_W, GRID_H, DIRS, COST_NORMAL, ENABLE_LAYERS, ELEVATORS,
)


def neighbors(cell):
    """與遊戲移動規則一致的相鄰格。

    雙層模式下座標是 (x, y, z)：朝電梯角格走一步，實際落點是另一層的
    同位置角格——所以電梯在圖上就是一條跨層邊，演算法自然學會搭電梯。
    """
    if ENABLE_LAYERS:
        x, y, z = cell
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                yield (nx, ny, 1 - z) if (nx, ny) in ELEVATORS else (nx, ny, z)
    else:
        x, y = cell
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                yield (nx, ny)


def bfs_path(start, goal, blocked):
    """步數最短路徑（不管地形代價，含頭尾）；到不了回 None。"""
    prev = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            path = [cur]
            while prev[cur] is not None:
                cur = prev[cur]
                path.append(cur)
            return path[::-1]
        for nxt in neighbors(cur):
            if nxt not in blocked and nxt not in prev:
                prev[nxt] = cur
                queue.append(nxt)
    return None


def dijkstra_path(start, goal, blocked, cost_fn):
    """依格子代價找最省體力的路徑（含頭尾）；到不了回 None。"""
    dist = {start: 0}
    prev = {start: None}
    heap = [(0, start)]
    while heap:
        d, cur = heapq.heappop(heap)
        if cur == goal:
            path = [cur]
            while prev[cur] is not None:
                cur = prev[cur]
                path.append(cur)
            return path[::-1]
        if d > dist.get(cur, 1e18):
            continue
        for nxt in neighbors(cur):
            if nxt in blocked:
                continue
            nd = d + cost_fn(nxt)
            if nd < dist.get(nxt, 1e18):
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(heap, (nd, nxt))
    return None


def astar_path(start, goal, blocked, cost_fn):
    """A* ＝ Dijkstra ＋ 啟發式（曼哈頓距離 × 最低格代價）。

    啟發式不高估剩餘代價（admissible：每步至少花 COST_NORMAL），
    所以路徑代價保證與 Dijkstra 相同——差別只在搜索有方向感、展開節點少，
    以及同代價路徑的平局選擇不同（行為對照的實驗點）。介面同 dijkstra_path。
    """
    def h(cell):
        return (abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])) * COST_NORMAL

    dist = {start: 0}
    prev = {start: None}
    heap = [(h(start), 0, start)]          # (f=g+h, g, cell)
    while heap:
        _f, g, cur = heapq.heappop(heap)
        if cur == goal:
            path = [cur]
            while prev[cur] is not None:
                cur = prev[cur]
                path.append(cur)
            return path[::-1]
        if g > dist.get(cur, 1e18):
            continue
        for nxt in neighbors(cur):
            if nxt in blocked:
                continue
            ng = g + cost_fn(nxt)
            if ng < dist.get(nxt, 1e18):
                dist[nxt] = ng
                prev[nxt] = cur
                heapq.heappush(heap, (ng + h(nxt), ng, nxt))
    return None


def path_cost(game, path):
    """整條路徑的體力代價（起點那格不算）。"""
    return sum(game.step_cost(c) for c in path[1:])


def walk_body(body, path, grow_at_end):
    """前向模擬：讓虛擬蛇沿 path 走完，回傳走完後的身體（頭在前）。"""
    body = list(body)
    last_i = len(path) - 1
    for i in range(1, len(path)):
        body.insert(0, path[i])
        if not (i == last_i and grow_at_end):
            body.pop()
    return body


def step_toward(head, path):
    """路徑的第一步換算成方向向量。"""
    nxt = path[1]
    return (nxt[0] - head[0], nxt[1] - head[1])
