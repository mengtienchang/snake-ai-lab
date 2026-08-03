# -*- coding: utf-8 -*-
"""漢米爾頓迴路＋編號捷徑（perturbed Hamiltonian）。

古典貪吃蛇的「標準答案」：預先算一條走遍每格恰好一次的封閉迴路，
沿著它走，身體永遠排在頭後面 → 數學上不可能撞到自己，理論上必定通關。

捷徑規則：允許沿迴圈方向「往前跳」，只要跳躍後頭的新編號仍落在
（尾編號, 蘋果編號] 的安全區間 —— 不越過尾巴、不跳過蘋果，身體在迴圈上
的順序不被切斷，安全證明保持成立。蛇短時近乎貪婪直線，蛇長時連續退化
回純迴圈，不需要任何切換閾值。

已知限制（實測數據）：前跳約束的幾何下界約 30+ 步/顆 —— 蘋果落在迴圈
「後方」時（機率約一半）只能繞整圈。收入 30/顆 的體力設定下收支打平，
必然慢性餓死。這不是實作缺陷，是古典安全保證與體力配速線的結構性衝突。
"""

from collections import deque

from environment.config import GRID_W, GRID_H, DIRS
from .pathfind import bfs_path, walk_body, step_toward

HAM_SHORTCUTS = True         # False = 純迴路（觀察古典行為本體）
HAM_SHORTCUT_MAXFILL = 0.5   # 體長超過棋盤這個比例後禁用捷徑（保守規則）


def _build_ham_cycle():
    """蛇行式漢米爾頓迴路（GRID_H 為偶數時成立）。回傳 (座標→序號, 序號→座標)。"""
    order = {}
    idx = 0
    for x in range(GRID_W):                     # 最上列由左到右
        order[(x, 0)] = idx; idx += 1
    for y in range(1, GRID_H):                  # 其餘列在 x=1..W-1 之間蛇行
        xs = range(GRID_W - 1, 0, -1) if y % 2 == 1 else range(1, GRID_W)
        for x in xs:
            order[(x, y)] = idx; idx += 1
    for y in range(GRID_H - 1, 0, -1):          # 最左行由下往上收尾
        order[(0, y)] = idx; idx += 1
    cells = [None] * len(order)
    for pos, i in order.items():
        cells[i] = pos
    return order, cells


HAM_ORDER, HAM_CELLS = _build_ham_cycle()


def auto_next_dir_ham(game):
    """回傳 (方向, 模式標籤)；無路可走時方向為 None。

    捷徑的找法：不是貪婪挑「單步跳最遠」，而是在安全跳躍圖上做 BFS
    （節點＝安全區間內的格子，邊＝編號嚴格遞增的相鄰跳躍），找出通往
    蘋果的最短安全路線 —— 此安全類別內的最優解。
    體力機制加疊前向模擬：抄近路前先虛擬走完整條路，確認吃到蘋果後
    仍追得到自己的尾巴，追不到就退回純迴圈。"""
    N = GRID_W * GRID_H
    head = game.snake[0]
    tail = game.snake[-1]
    t = HAM_ORDER[tail]

    def rel(cell):
        return (HAM_ORDER[cell] - t) % N        # 以尾巴為原點的迴路位置

    rel_head = rel(head)
    body = set(game.snake)
    target = game.food

    def ok(cell):
        return (0 <= cell[0] < GRID_W and 0 <= cell[1] < GRID_H
                and cell not in body and cell not in game.obstacles)

    # --- 捷徑：安全跳躍圖上的 BFS ---
    if (HAM_SHORTCUTS and target is not None
            and len(game.snake) < N * HAM_SHORTCUT_MAXFILL):
        rel_target = rel(target)
        prev = {head: None}
        queue = deque([head])
        found = False
        while queue:
            cur = queue.popleft()
            if cur == target:
                found = True
                break
            rc = rel(cur)
            for dx, dy in DIRS:
                n = (cur[0] + dx, cur[1] + dy)
                if n in prev or not ok(n):
                    continue
                if game.portals and n in game.portals:
                    continue                    # 傳送會打亂迴圈順序
                rn = rel(n)
                if rn <= rc or rn > rel_target:  # 只准沿迴圈方向前跳、不跳過蘋果
                    continue
                prev[n] = cur
                queue.append(n)
        if found:
            path = [target]
            while prev[path[-1]] is not None:
                path.append(prev[path[-1]])
            path.reverse()
            if len(path) >= 2:
                # 前向模擬：吃完之後追得到尾巴才走
                after = walk_body(game.snake, path, grow_at_end=True)
                blocked = (set(after[:-1]) | game.obstacles) - {after[-1]}
                if bfs_path(after[0], after[-1], blocked) is not None:
                    nxt = path[1]
                    label = ("循環捷徑" if rel(nxt) > rel_head + 1 else "純循環")
                    return (nxt[0] - head[0], nxt[1] - head[1]), label

    # --- 純迴圈：走迴圈上的下一格（下一格是尾巴且這步不長身體時也可走）---
    nxt = HAM_CELLS[(HAM_ORDER[head] + 1) % N]
    if ok(nxt) or (nxt == tail and game.grow == 0):
        return (nxt[0] - head[0], nxt[1] - head[1]), "純循環"

    # 迴路被打亂（傳送門等因素）：退回跟尾巴求生
    path = bfs_path(head, tail, set(game.snake[1:-1]) | game.obstacles)
    if path and len(path) >= 2:
        return step_toward(head, path), "脫軌求生"
    for d in DIRS:
        n = (head[0] + d[0], head[1] + d[1])
        if ok(n):
            return d, "苟活"
    return None, "無路可走"
