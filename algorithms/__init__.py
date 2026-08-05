# -*- coding: utf-8 -*-
"""自動模式的演算法，全部並存、遊戲內下拉選單（或按 G）切換對照：

    pathfind.py      共用尋路工具（BFS / Dijkstra / 前向模擬）
    pathfind_lib.py  外部庫的同介面原語（python-pathfinding / networkx）
    greedy_bfs.py    BFS 貪婪流（原版對照組：最短路＋尾巴安全檢查）
    greedy_dij.py    Dijkstra 貪婪流（按體力代價找路＋體力/藍蘋果規則）
    hamilton.py      漢米爾頓迴路＋編號捷徑（古典必勝解法的現代版）
    graft.py         嫁接流（前期 DIJ 衝分攢體力，蛇長達標切 HAM 保命）

每個策略函式的介面相同：fn(game) -> (方向 or None, 模式標籤)。
新演算法照這個介面寫好後，加進下面的 AUTO_ALGOS 就會出現在遊戲裡。
"""

from functools import partial

from environment.config import ENABLE_LAYERS

from .greedy_bfs import auto_next_dir_bfs
from .greedy_dij import auto_next_dir_dij
from .hamilton import auto_next_dir_ham
from .graft import auto_next_dir_graft
from .pathfind import astar_path

AUTO_ALGOS = [
    ("BFS", auto_next_dir_bfs),
    ("DIJ", auto_next_dir_dij),
    # A*：同 DIJ 策略層，原語換 A*——代價保證相同，只有平局選擇不同
    ("A*", partial(auto_next_dir_dij, path_fn=astar_path)),
]

if not ENABLE_LAYERS:
    # HAM／嫁接依賴單層迴圈編號，還不會搭電梯，只在單層服役
    AUTO_ALGOS += [
        ("HAM", auto_next_dir_ham),
        ("嫁接", auto_next_dir_graft),
    ]

# 外部庫版：同一套策略層，尋路原語換成成熟第三方庫，遊戲內直接對照。
# （雙層模式下三個庫版統一走 networkx 圖，見 pathfind_lib 檔頭說明）
# 套件沒裝（networkx / pathfinding）就自動略過，遊戲照常能玩。
try:
    from .pathfind_lib import lib_bfs_path, lib_dijkstra_path, lib_astar_path
except ImportError:
    pass
else:
    AUTO_ALGOS += [
        ("BFS·庫", partial(auto_next_dir_bfs, path_fn=lib_bfs_path)),
        ("DIJ·庫", partial(auto_next_dir_dij, path_fn=lib_dijkstra_path)),
        ("A*·庫", partial(auto_next_dir_dij, path_fn=lib_astar_path)),
    ]
