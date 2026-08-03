# -*- coding: utf-8 -*-
"""環境參數與開關 —— 想調整遊戲規則，只改這個檔。"""

# ---- 棋盤 ----
GRID_W, GRID_H = 28, 22

# ---- 方向 ----
UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
DIRS = (UP, DOWN, LEFT, RIGHT)

# ---- 速度 ----
START_FPS = 8            # 起始速度（每秒移動格數）
MAX_FPS = 20             # 速度上限
SPEEDUP_EVERY = 3        # 每吃幾顆紅蘋果加速一次

# ---- 環境開關 ----
# 關掉石頭、碎石地、傳送門 → 乾淨棋盤，觀察演算法本身的行為。
# （石頭會把蘋果圍成死路；傳送門會打亂 HAM 迴路的隊形；要復原改回 True）
ENABLE_ROCKS = False
ENABLE_ROUGH = False
ENABLE_PORTALS = False

# ---- 物件生成節奏 ----
GOLD_EVERY = 5           # 每吃幾顆紅蘋果出金蘋果
GOLD_TTL = 45            # 金蘋果存活步數
BLUE_EVERY = 6           # 每吃幾顆紅蘋果出藍蘋果
BLUE_TTL = 60
PORTAL_EVERY = 7         # 每吃幾顆紅蘋果出一對傳送門
PORTAL_TTL = 80
ITEM_BLINK = 14          # 限時物件剩幾步開始閃爍
ROCK_EVERY = 4           # 每吃幾顆紅蘋果長一塊石頭
ROCK_SAFE_DIST = 4       # 石頭不出現在離蛇頭這麼近的地方

# ---- 體力 ----
ENERGY_START = 100
ENERGY_MAX = 9999        # 幾乎不設限：前期超額進食可以累積成儲備
ENERGY_BAR_REF = 160     # 體力條「畫滿」的基準（超過就滿格，數字繼續漲）
COST_NORMAL = 1          # 平地一步的體力消耗
COST_ROUGH = 3           # 碎石地一步的體力消耗
ENERGY_RED = 30          # 紅蘋果回補 —— 注意：這個數字就是「配速線」，
ENERGY_GOLD = 40         # 平均 30 步內吃不到一顆就是慢性死亡；
ENERGY_BLUE = 10         # 調它可以決定哪個流派的演算法活得下來

# ---- 藍蘋果 ----
BLUE_SCORE_PENALTY = 20  # 吃藍蘋果扣的分
BLUE_SHRINK = 3          # 吃藍蘋果淨減的節數

# ---- 碎石地生成 ----
ROUGH_BLOBS = 5          # 區塊數
ROUGH_BLOB_SIZE = (8, 15)  # 每塊的格數範圍
