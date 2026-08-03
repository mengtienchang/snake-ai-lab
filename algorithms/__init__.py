# -*- coding: utf-8 -*-
"""自動模式的演算法，全部並存、遊戲內按 G 切換對照：

    pathfind.py     共用尋路工具（BFS / Dijkstra / 前向模擬）
    greedy_bfs.py   BFS 貪婪流（原版對照組：最短路＋尾巴安全檢查）
    greedy_dij.py   Dijkstra 貪婪流（按體力代價找路＋體力/藍蘋果規則）
    hamilton.py     漢米爾頓迴路＋編號捷徑（古典必勝解法的現代版）

每個策略函式的介面相同：fn(game) -> (方向 or None, 模式標籤)。
新演算法照這個介面寫好後，加進下面的 AUTO_ALGOS 就會出現在遊戲裡。
"""

from .greedy_bfs import auto_next_dir_bfs
from .greedy_dij import auto_next_dir_dij
from .hamilton import auto_next_dir_ham

AUTO_ALGOS = [
    ("BFS", auto_next_dir_bfs),
    ("DIJ", auto_next_dir_dij),
    ("HAM", auto_next_dir_ham),
]
