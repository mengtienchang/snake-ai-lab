# -*- coding: utf-8 -*-
"""Dijkstra 貪婪流：按體力代價找最省的路，加上體力與藍蘋果的判斷。

比 BFS 多的規則：會繞開碎石地、路費付不起的路不走、體力恐慌時賭一把、
蛇太長時考慮吃藍蘋果減重 —— 「環境越複雜、手寫規則越寫不完」的活例子。
"""

from environment.config import GRID_W, GRID_H, DIRS
from .pathfind import dijkstra_path, path_cost, walk_body, step_toward

ENERGY_PANIC = 45      # 體力低於這個值進入「先吃再說」模式
BLUE_WORTH_LEN = 45    # 蛇長超過這個值，藍蘋果才值得吃


def auto_next_dir_dij(game, path_fn=dijkstra_path):
    """回傳 (方向, 模式標籤)；無路可走時方向為 None。

    path_fn 可換成同介面的其他 Dijkstra 原語（如 pathfind_lib.lib_dijkstra_path），
    策略邏輯不變，專門用來對照手寫版與外部庫。
    """
    head = game.snake[0]
    rocks = game.obstacles
    body_block = set(game.snake[:-1]) | rocks
    cost = game.step_cost

    def tail_reachable_after(path):
        after = walk_body(game.snake, path, grow_at_end=True)
        blocked = (set(after[:-1]) | rocks) - {after[-1]}
        return path_fn(after[0], after[-1], blocked, cost) is not None

    # 目標優先序：蛇太長先考慮藍蘋果減重 → 金蘋果（來得及才追）→ 紅蘋果
    targets = []
    if game.blue is not None and len(game.snake) >= BLUE_WORTH_LEN:
        targets.append((game.blue, game.blue_left, "追藍蘋果"))
    if game.gold is not None:
        targets.append((game.gold, game.gold_left, "追金蘋果"))
    if game.food is not None:
        targets.append((game.food, None, "追紅蘋果"))

    fallback = None    # 體力恐慌時「不做安全檢查也要走」的備案
    for target, ttl, label in targets:
        path = path_fn(head, target, body_block, cost)
        if not path or len(path) < 2:
            continue
        if ttl is not None and len(path) - 1 > ttl:
            continue
        if path_cost(game, path) >= game.energy:
            continue                      # 走到就先餓死的路不走
        if tail_reachable_after(path):
            return step_toward(head, path), label
        if fallback is None:
            fallback = path

    # 體力恐慌：安全的路不存在，但有能走到食物的路 → 賭一把
    if game.energy < ENERGY_PANIC and fallback is not None:
        return step_toward(head, fallback), "恐慌賭路"

    # 跟著尾巴繞（等局面打開）
    tail = game.snake[-1]
    path = path_fn(head, tail, set(game.snake[1:-1]) | rocks, cost)
    if path and len(path) >= 2:
        return step_toward(head, path), "跟尾巴等機會"

    for d in DIRS:
        nxt = (head[0] + d[0], head[1] + d[1])
        if (0 <= nxt[0] < GRID_W and 0 <= nxt[1] < GRID_H
                and nxt not in body_block):
            return d, "苟活"
    return None, "無路可走"
