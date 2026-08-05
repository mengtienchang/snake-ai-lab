# -*- coding: utf-8 -*-
"""BFS 貪婪流（原版對照組，決策邏輯保持原封不動）。

最短路＋尾巴安全檢查＋跟尾巴繞。不認識地形代價、體力、藍蘋果 ——
在體力機制下「跟尾巴等機會」會慢性餓死，這正是要觀察的行為。
"""

from .pathfind import bfs_path, neighbors, walk_body, step_toward


def auto_next_dir_bfs(game, path_fn=bfs_path):
    """回傳 (方向, 模式標籤)；無路可走時方向為 None。

    path_fn 可換成同介面的其他 BFS 原語（如 pathfind_lib.lib_bfs_path），
    策略邏輯不變，專門用來對照手寫版與外部庫。
    """
    head = game.snake[0]
    rocks = game.obstacles
    body_block = set(game.snake[:-1]) | rocks

    def tail_reachable_after(path):
        after = walk_body(game.snake, path, grow_at_end=True)
        blocked = (set(after[:-1]) | rocks) - {after[-1]}
        return path_fn(after[0], after[-1], blocked) is not None

    targets = []
    if game.gold is not None:
        targets.append((game.gold, game.gold_left, "追金蘋果"))
    if game.food is not None:
        targets.append((game.food, None, "追紅蘋果"))
    for target, ttl, label in targets:
        path = path_fn(head, target, body_block)
        if not path or len(path) < 2:
            continue
        if ttl is not None and len(path) - 1 > ttl:
            continue
        if tail_reachable_after(path):
            return step_toward(head, path), label

    tail = game.snake[-1]
    path = path_fn(head, tail, set(game.snake[1:-1]) | rocks)
    if path and len(path) >= 2:
        return step_toward(head, path), "跟尾巴等機會"

    for nxt in neighbors(head):
        if nxt not in body_block:
            return step_toward(head, [head, nxt]), "苟活"
    return None, "無路可走"
