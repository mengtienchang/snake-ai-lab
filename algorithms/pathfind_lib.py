# -*- coding: utf-8 -*-
"""成熟第三方庫的尋路原語 —— 跟手寫版同介面，拿來對比。

    lib_bfs_path       python-pathfinding 的 BreadthFirstFinder（遊戲網格專用庫）
    lib_dijkstra_path  networkx 的 dijkstra_path（圖論標準庫）
    lib_astar_path     python-pathfinding 的 AStarFinder（加權網格 A*）

介面與 pathfind.py 的手寫版完全一致（含頭尾的路徑列表，到不了回 None），
所以策略層可以整組換掉原語做對照。注意：庫只提供「找路」——
尾巴安全檢查、體力規則、漢米爾頓迴路這些策略層，沒有現成庫可替代。

雙層模式：三個庫版統一改走 networkx 圖——鄰接直接重用 pathfind.neighbors()
（電梯＝跨層邊），跟遊戲規則零偏差。python-pathfinding 是矩陣式 2D 庫，
不支援第三維，只在單層模式服役。
"""

import networkx as nx
from pathfinding.core.grid import Grid as PFGrid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder

from environment.config import GRID_W, GRID_H, DIRS, ENABLE_LAYERS
from .pathfind import neighbors


def _layer_graph(start, blocked, cost_fn=None):
    """雙層圖：節點 (x,y,z)，邊照 neighbors()（含電梯跨層邊）。"""
    graph = nx.DiGraph()
    for z in (0, 1):
        for x in range(GRID_W):
            for y in range(GRID_H):
                cur = (x, y, z)
                if cur in blocked and cur != start:
                    continue
                for nxt in neighbors(cur):
                    if nxt in blocked:
                        continue
                    graph.add_edge(cur, nxt,
                                   weight=cost_fn(nxt) if cost_fn else 1)
    return graph


def lib_bfs_path(start, goal, blocked):
    """python-pathfinding 的 BFS。矩陣 1=可走、0=障礙。雙層走 networkx。"""
    if start == goal:
        return [start]
    if ENABLE_LAYERS:
        try:
            return nx.shortest_path(_layer_graph(start, blocked), start, goal)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    matrix = [[0 if (x, y) in blocked else 1 for x in range(GRID_W)]
              for y in range(GRID_H)]
    # 起點所在格必須可走（起點是蛇頭，可能被算進 blocked 之外本來就該可走）
    matrix[start[1]][start[0]] = 1
    if matrix[goal[1]][goal[0]] == 0:
        return None
    grid = PFGrid(matrix=matrix)
    finder = BreadthFirstFinder()
    path, _runs = finder.find_path(grid.node(*start), grid.node(*goal), grid)
    if not path:
        return None
    return [(n.x, n.y) for n in path]


def lib_astar_path(start, goal, blocked, cost_fn):
    """python-pathfinding 的加權 A*。矩陣值＝踏進該格的代價，0＝障礙。
    雙層走 networkx 的 astar_path（曼哈頓啟發式跨層仍 admissible）。"""
    if start == goal:
        return [start]
    if ENABLE_LAYERS:
        try:
            return nx.astar_path(
                _layer_graph(start, blocked, cost_fn), start, goal,
                heuristic=lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1]),
                weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    matrix = [[0 if (x, y) in blocked else cost_fn((x, y))
               for x in range(GRID_W)] for y in range(GRID_H)]
    matrix[start[1]][start[0]] = max(1, matrix[start[1]][start[0]])
    if matrix[goal[1]][goal[0]] == 0:
        return None
    grid = PFGrid(matrix=matrix)
    finder = AStarFinder()
    path, _runs = finder.find_path(grid.node(*start), grid.node(*goal), grid)
    if not path:
        return None
    return [(n.x, n.y) for n in path]


def lib_dijkstra_path(start, goal, blocked, cost_fn):
    """networkx 的 Dijkstra。把「踏進某格的體力代價」放在指向該格的邊上。"""
    if start == goal:
        return [start]
    if ENABLE_LAYERS:
        try:
            return nx.dijkstra_path(_layer_graph(start, blocked, cost_fn),
                                    start, goal)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    if goal in blocked:
        return None
    graph = nx.DiGraph()
    for x in range(GRID_W):
        for y in range(GRID_H):
            cur = (x, y)
            if cur in blocked and cur != start:
                continue
            for dx, dy in DIRS:
                nxt = (x + dx, y + dy)
                if not (0 <= nxt[0] < GRID_W and 0 <= nxt[1] < GRID_H):
                    continue
                if nxt in blocked:
                    continue
                graph.add_edge(cur, nxt, weight=cost_fn(nxt))
    try:
        return nx.dijkstra_path(graph, start, goal)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
