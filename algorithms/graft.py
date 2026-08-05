# -*- coding: utf-8 -*-
"""嫁接流：前期 DIJ 衝分攢體力，後期切換 HAM 保命慢燒。

理據（來自 1000 局批量數據）：
    DIJ  平均 2176：吃得快、體力儲備越攢越厚，但 40% 死於幾何自困——
         蛇一長，貪婪路線就可能把自己圍死。
    HAM  平均 446：數學上不可能自困，但前跳約束的幾何下界 ~32 步/顆
         略高於紅蘋果 +30 的配速線，每顆淨虧 2~5 體力，孤軍必餓死。

嫁接把兩個死因互補：DIJ 在蛇還短、自困風險低的階段高效進食，
體力上限near無限（ENERGY_MAX 9999）可以攢出幾百點儲備；
蛇長進入自困風險區之前切到 HAM——之後每顆蘋果的小額虧損由儲備買單，
自困死法則被 HAM 的安全保證整個抹掉。

切換條件：蛇長 ≥ GRAFT_LEN 後走 HAM。函式無狀態，但切換事實上不可逆：
HAM 不吃藍蘋果，蛇長只增不減，不會在門檻上來回抖動。
剛切換時身體不在迴圈順序上，HAM 內建的「脫軌求生」（跟尾巴繞）會
自動把隊形收斂回迴圈——這是 hamilton.py 原有的 fallback，嫁接直接繼承。

模式標籤加上「衝刺·」／「續航·」前綴，行為記錄裡能看出當下處於哪一段。
"""

from .greedy_dij import auto_next_dir_dij
from .hamilton import auto_next_dir_ham

GRAFT_LEN = 80    # 蛇長達到這個值就切換到 HAM（調它做敏感度實驗）


def auto_next_dir_graft(game):
    """回傳 (方向, 模式標籤)；無路可走時方向為 None。"""
    if len(game.snake) < GRAFT_LEN:
        d, mode = auto_next_dir_dij(game)
        return d, "衝刺·" + mode
    d, mode = auto_next_dir_ham(game)
    return d, "續航·" + mode
