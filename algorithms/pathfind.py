# -*- coding: utf-8 -*-
"""共用尋路工具：BFS、Dijkstra、路徑代價、前向模擬。"""

import heapq
from collections import deque

from environment.config import GRID_W, GRID_H, DIRS


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
        x, y = cur
        for dx, dy in DIRS:
            nxt = (x + dx, y + dy)
            if (0 <= nxt[0] < GRID_W and 0 <= nxt[1] < GRID_H
                    and nxt not in blocked and nxt not in prev):
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
        x, y = cur
        for dx, dy in DIRS:
            nxt = (x + dx, y + dy)
            if not (0 <= nxt[0] < GRID_W and 0 <= nxt[1] < GRID_H):
                continue
            if nxt in blocked:
                continue
            nd = d + cost_fn(nxt)
            if nd < dist.get(nxt, 1e18):
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(heap, (nd, nxt))
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
