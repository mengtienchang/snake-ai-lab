# -*- coding: utf-8 -*-
"""貪吃蛇 —— 介面層與入口。

專案結構：
    snake_game.py    本檔：畫面、音效、輸入、行為記錄、主迴圈（介面層）
    environment/     環境機制
        config.py    所有可調參數與開關（改遊戲規則、開關雙層棋盤來這裡）
        game.py      Game 類 —— 規則本體，可無視窗執行
    algorithms/      自動模式的演算法（介面統一，下拉選單／G 鍵切換對照）
        pathfind.py  手寫 BFS/Dijkstra/A* ＋ neighbors（雙層鄰接）
        pathfind_lib.py  外部庫同介面原語
        greedy_bfs.py / greedy_dij.py / hamilton.py / graft.py

操作：
    方向鍵 / WASD      轉向
    空白鍵 / P（或點上方「暫停」按鈕）  暫停／繼續
    R（或 Enter）      重新開始 —— 用實體按鍵判斷，中文輸入法開著也有效
    T（或點上方按鈕）  自動模式開／關
    G                  循環切換演算法；點上方「尋路」按鈕開下拉選單直接選
    ESC                離開

行為記錄：行為記錄.txt（人看）＋ 行為記錄.jsonl（程式分析用）
最高分：highscore.json

執行：
    .venv/bin/python snake_game.py     （或雙擊 啟動貪吃蛇.command）
"""

import datetime
import json
import math
import os
import random
import sys

import pygame

from environment.config import (
    GRID_W, GRID_H, MAX_FPS, ITEM_BLINK, ENERGY_BAR_REF,
    UP, DOWN, LEFT, RIGHT,
    ENABLE_LAYERS, ELEVATORS,
)
from environment import Game
from algorithms import AUTO_ALGOS

# 舊測試腳本的相容匯出（import snake_game as sg 之後照舊能用）
from algorithms.pathfind import bfs_path, dijkstra_path, walk_body, path_cost  # noqa: F401
from algorithms.greedy_bfs import auto_next_dir_bfs                            # noqa: F401
from algorithms.greedy_dij import auto_next_dir_dij                            # noqa: F401
from algorithms.hamilton import auto_next_dir_ham, HAM_ORDER, HAM_CELLS        # noqa: F401

# ---------------------------------------------------------------- 介面設定

CELL = 21 if ENABLE_LAYERS else 24   # 雙層並排時縮小格子，視窗才放得下
TOP_BAR = 74                       # 上方資訊區（含體力條）
BOARD_W = GRID_W * CELL
LAYER_GAP = 20                     # 雙層模式兩片棋盤的中縫
BOTTOM = 24 if ENABLE_LAYERS else 0  # 下方層標籤列
if ENABLE_LAYERS:
    WIDTH = BOARD_W * 2 + LAYER_GAP
else:
    WIDTH = BOARD_W
HEIGHT = GRID_H * CELL + TOP_BAR + BOTTOM
ELEV_COLOR = (120, 210, 235)
ELEV_DIM = (60, 110, 125)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISCORE_FILE = os.path.join(_BASE_DIR, "highscore.json")
BEHAVIOR_LOG = os.path.join(_BASE_DIR, "行為記錄.txt")
BEHAVIOR_JSONL = os.path.join(_BASE_DIR, "行為記錄.jsonl")

# 配色
BG_DARK = (28, 32, 38)
BG_A = (44, 50, 58)
BG_B = (48, 55, 64)
ROUGH_A = (38, 40, 44)
ROUGH_B = (41, 44, 48)
ROUGH_DOT = (30, 31, 34)
BAR_BG = (20, 23, 27)
HEAD_COLOR = (110, 220, 130)
TAIL_COLOR = (40, 95, 60)
FOOD = (230, 90, 80)
FOOD_SHINE = (255, 170, 160)
GOLD = (245, 200, 80)
GOLD_GLOW = (255, 230, 150)
BLUE = (90, 150, 235)
BLUE_GLOW = (160, 200, 255)
PORTAL = (80, 200, 220)
ROCK = (95, 100, 108)
ROCK_HI = (130, 136, 145)
TEXT = (230, 232, 235)
TEXT_DIM = (140, 146, 155)
ENERGY_OK = (96, 200, 120)
ENERGY_MID = (240, 200, 90)
ENERGY_LOW = (230, 90, 80)

# 實體按鍵（scancode ＝ 鍵盤位置，中文輸入法開著也有效）
SCAN_DIR = {
    pygame.KSCAN_UP: UP, pygame.KSCAN_W: UP,
    pygame.KSCAN_DOWN: DOWN, pygame.KSCAN_S: DOWN,
    pygame.KSCAN_LEFT: LEFT, pygame.KSCAN_A: LEFT,
    pygame.KSCAN_RIGHT: RIGHT, pygame.KSCAN_D: RIGHT,
}
SCAN_PAUSE = (pygame.KSCAN_SPACE, pygame.KSCAN_P)
SCAN_RESTART = (pygame.KSCAN_R, pygame.KSCAN_RETURN, pygame.KSCAN_KP_ENTER)
SCAN_AUTO = pygame.KSCAN_T
SCAN_ALGO = pygame.KSCAN_G

AUTO_BTN = pygame.Rect(WIDTH // 2 - 128, 8, 120, 34)
ALGO_BTN = pygame.Rect(WIDTH // 2 + 2, 8, 126, 34)
PAUSE_BTN = pygame.Rect(WIDTH // 2 + 138, 8, 56, 34)
ALGO_OPT_H = 30                    # 下拉選單每列高度


def algo_option_rects():
    """下拉選單各選項的矩形（緊貼在「尋路」按鈕下方）。"""
    return [pygame.Rect(ALGO_BTN.x, ALGO_BTN.bottom + 4 + i * ALGO_OPT_H,
                        ALGO_BTN.w, ALGO_OPT_H)
            for i in range(len(AUTO_ALGOS))]


# ---------------------------------------------------------------- 行為記錄

def log_line(text, echo=True, data=None):
    """行為記錄，雙軌輸出：

    - 人看的：印在終端機＋寫進 行為記錄.txt（原樣的中文旁白）
    - 程式讀的：data 不為 None 時，再寫一行 JSON 進 行為記錄.jsonl
      （JSONL：一行一物件，追加安全，之後要統計/畫圖直接逐行 json.loads）
    """
    if echo:
        print(text)
    try:
        with open(BEHAVIOR_LOG, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except IOError:
        pass
    if data is not None:
        data = dict(data)
        data.setdefault("ts", datetime.datetime.now().isoformat(timespec="seconds"))
        try:
            with open(BEHAVIOR_JSONL, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(data, ensure_ascii=False) + "\n")
        except IOError:
            pass


# ---------------------------------------------------------------- 最高分存檔

def load_hiscore():
    try:
        with open(HISCORE_FILE, "r", encoding="utf-8") as fh:
            return int(json.load(fh).get("best", 0))
    except (IOError, ValueError):
        return 0


def save_hiscore(best):
    try:
        with open(HISCORE_FILE, "w", encoding="utf-8") as fh:
            json.dump({"best": int(best)}, fh)
    except IOError:
        pass


# ---------------------------------------------------------------- 字型與音效

def load_font(size, bold=False):
    """挑一個能顯示中文的字型。pygame 的字型名是正規化過的（全小寫、去空格）。"""
    available = set(pygame.font.get_fonts())
    candidates = ("pingfangtc", "pingfang", "stheitimedium", "stheitilight",
                  "hiraginosansgb", "arialunicode", "microsoftjhenghei",
                  "notosanscjktc", "notosanscjksc", "wenquanyimicrohei")
    for name in candidates:
        if name not in available:
            continue
        font = pygame.font.SysFont(name, size, bold=bold)
        m = font.metrics("測")
        if m and m[0] is not None:
            return font
    return pygame.font.Font(None, size)


def _square_wave(freq, ms, vol=0.25):
    rate = 22050
    n = int(rate * ms / 1000)
    period = rate / freq
    buf = bytearray()
    for i in range(n):
        v = vol * (1.0 if (i % period) < period / 2 else -1.0)
        v *= 1.0 - i / n
        buf += int(v * 32767).to_bytes(2, "little", signed=True)
    return pygame.mixer.Sound(buffer=bytes(buf))


def load_sounds():
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        return {
            "eat": _square_wave(880, 70),
            "gold": _square_wave(1320, 150, 0.3),
            "blue": _square_wave(520, 120, 0.25),
            "portal": _square_wave(1040, 90, 0.2),
            "die": _square_wave(130, 300, 0.3),
        }
    except pygame.error:
        return {}


# ---------------------------------------------------------------- 粒子特效

class Particles(object):
    def __init__(self):
        self.items = []

    def burst(self, pos, color, count=14):
        cx, cy = cell_rect(pos).center
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(40, 160)
            self.items.append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * spd, "vy": math.sin(ang) * spd - 40,
                "life": random.uniform(0.35, 0.7), "age": 0.0,
                "color": color,
            })

    def update(self, dt):
        for p in self.items:
            p["age"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 300 * dt
        self.items = [p for p in self.items if p["age"] < p["life"]]

    def draw(self, screen):
        for p in self.items:
            k = 1.0 - p["age"] / p["life"]
            size = max(1, int(5 * k))
            pygame.draw.rect(screen, p["color"],
                             (int(p["x"]), int(p["y"]), size, size))


# ---------------------------------------------------------------- 畫面

def cell_rect(pos):
    x, y = pos[0], pos[1]
    ox = 0
    if ENABLE_LAYERS and len(pos) > 2 and pos[2] == 1:
        ox = BOARD_W + LAYER_GAP           # 下層畫在右邊那片
    return pygame.Rect(ox + x * CELL, TOP_BAR + y * CELL, CELL, CELL)


def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_board(screen, game):
    layers = (0, 1) if ENABLE_LAYERS else (None,)
    for z in layers:
        for y in range(GRID_H):
            for x in range(GRID_W):
                pos = (x, y) if z is None else (x, y, z)
                if pos in game.rough:
                    color = ROUGH_A if (x + y) % 2 == 0 else ROUGH_B
                else:
                    color = BG_A if (x + y) % 2 == 0 else BG_B
                r = cell_rect(pos)
                pygame.draw.rect(screen, color, r)
                if pos in game.rough:      # 碎石斑點
                    pygame.draw.circle(screen, ROUGH_DOT, (r.x + 7, r.y + 8), 2)
                    pygame.draw.circle(screen, ROUGH_DOT, (r.x + 16, r.y + 15), 2)


def draw_layers_chrome(screen, small):
    """雙層模式的框線、層標籤與四角電梯。"""
    if not ENABLE_LAYERS:
        return
    for z, label in ((0, "上層"), (1, "下層")):
        ox = 0 if z == 0 else BOARD_W + LAYER_GAP
        txt = small.render(label, True, TEXT_DIM)
        screen.blit(txt, (ox + BOARD_W // 2 - txt.get_width() // 2,
                          HEIGHT - BOTTOM + 3))
        for ex, ey in ELEVATORS:
            r = cell_rect((ex, ey, z))
            pygame.draw.rect(screen, (34, 48, 54), r)
            pygame.draw.rect(screen, ELEV_COLOR, r.inflate(-2, -2), 2,
                             border_radius=4)
            cx, cy = r.center
            q = CELL // 4                      # ▲▼ 上下箭頭
            pygame.draw.polygon(screen, ELEV_COLOR,
                                [(cx - q, cy - 1), (cx + q, cy - 1), (cx, cy - q - 2)])
            pygame.draw.polygon(screen, ELEV_DIM,
                                [(cx - q, cy + 1), (cx + q, cy + 1), (cx, cy + q + 2)])


def draw_portals(screen, game, now_ms):
    if not game.portals:
        return
    blink = game.portal_left <= ITEM_BLINK and game.portal_left % 2 == 0
    if blink:
        return
    for pos in game.portals:
        r = cell_rect(pos).inflate(-3, -3)
        pygame.draw.rect(screen, PORTAL, r, 2, border_radius=6)
        for k in (-6, 0, 6):           # 斜紋記號
            pygame.draw.line(screen, PORTAL,
                             (r.left + max(0, k), r.bottom - max(0, -k) - 1),
                             (r.right - max(0, -k) - 1, r.top + max(0, k)), 2)


def draw_rocks(screen, game):
    for pos in game.obstacles:
        r = cell_rect(pos).inflate(-4, -4)
        pygame.draw.rect(screen, ROCK, r, border_radius=6)
        pygame.draw.rect(screen, ROCK_HI, r.inflate(-8, -12).move(0, -3),
                         border_radius=4)


def draw_snake(screen, game):
    n = max(1, len(game.snake) - 1)
    pad = max(2, round(CELL / 8))          # 縮邊與圓角隨格子大小等比縮放
    radius = max(4, round(CELL * 0.29))
    for i, pos in enumerate(reversed(game.snake)):
        idx = len(game.snake) - 1 - i
        color = lerp_color(HEAD_COLOR, TAIL_COLOR, idx / n)
        pygame.draw.rect(screen, color, cell_rect(pos).inflate(-pad, -pad),
                         border_radius=radius)
    head = cell_rect(game.snake[0])
    dx, dy = game.direction
    cx, cy = head.center
    off, spread = CELL // 5, CELL // 5
    eye_r = max(2, round(CELL / 8))
    eyes = ([(cx + dx * off, cy - spread), (cx + dx * off, cy + spread)] if dx
            else [(cx - spread, cy + dy * off), (cx + spread, cy + dy * off)])
    for ex, ey in eyes:
        pygame.draw.circle(screen, (25, 40, 30), (ex, ey), eye_r)


def draw_items(screen, game, now_ms):
    if game.food:
        r = cell_rect(game.food)
        s = max(2, round(CELL / 8))
        pygame.draw.circle(screen, FOOD, r.center, CELL // 2 - s)
        pygame.draw.circle(screen, FOOD_SHINE, (r.centerx - s, r.centery - s), s)
    pulse = 2 + int(2 * abs(math.sin(now_ms / 200.0)))
    for item, left, main_c, glow in ((game.gold, game.gold_left, GOLD, GOLD_GLOW),
                                     (game.blue, game.blue_left, BLUE, BLUE_GLOW)):
        if item is None:
            continue
        if left <= ITEM_BLINK and left % 2 == 0:
            continue
        r = cell_rect(item)
        pygame.draw.circle(screen, glow, r.center, CELL // 2 - 1 + pulse, 2)
        pygame.draw.circle(screen, main_c, r.center, CELL // 2 - 4)
        pygame.draw.circle(screen, (245, 248, 252),
                           (r.centerx - 3, r.centery - 3), 3)


def draw_bar(screen, game, best, auto, algo_idx, mode_text, font, small):
    pygame.draw.rect(screen, BAR_BG, (0, 0, WIDTH, TOP_BAR))
    screen.blit(font.render("分數 %d" % game.score, True, GOLD), (14, 8))
    screen.blit(small.render("最高 %d" % best, True, TEXT_DIM), (170, 18))
    speed = small.render("速度 %d / %d" % (game.fps, MAX_FPS), True, TEXT_DIM)
    screen.blit(speed, (WIDTH - speed.get_width() - 14, 6))
    info = small.render("長度 %d　石頭 %d" % (len(game.snake), len(game.obstacles)),
                        True, TEXT_DIM)
    screen.blit(info, (WIDTH - info.get_width() - 14, 28))

    # 自動模式按鈕 ＋ 演算法切換按鈕
    pygame.draw.rect(screen, (46, 120, 70) if auto else (58, 64, 74),
                     AUTO_BTN, border_radius=8)
    if auto:
        pygame.draw.rect(screen, HEAD_COLOR, AUTO_BTN, 2, border_radius=8)
    label = small.render("自動模式：%s" % ("開" if auto else "關"),
                         True, TEXT if auto else TEXT_DIM)
    screen.blit(label, (AUTO_BTN.centerx - label.get_width() // 2,
                        AUTO_BTN.centery - label.get_height() // 2))

    algo_name = AUTO_ALGOS[algo_idx][0]
    pygame.draw.rect(screen, (52, 70, 100) if auto else (58, 64, 74),
                     ALGO_BTN, border_radius=8)
    label = small.render("尋路：%s ▾" % algo_name,
                         True, TEXT if auto else TEXT_DIM)
    screen.blit(label, (ALGO_BTN.centerx - label.get_width() // 2,
                        ALGO_BTN.centery - label.get_height() // 2))

    # 暫停按鈕（截圖好幫手；空白鍵/P 照舊有效）
    pygame.draw.rect(screen, (120, 96, 46) if game.paused else (58, 64, 74),
                     PAUSE_BTN, border_radius=8)
    if game.paused:
        pygame.draw.rect(screen, GOLD, PAUSE_BTN, 2, border_radius=8)
    label = small.render("繼續" if game.paused else "暫停",
                         True, TEXT if game.paused else TEXT_DIM)
    screen.blit(label, (PAUSE_BTN.centerx - label.get_width() // 2,
                        PAUSE_BTN.centery - label.get_height() // 2))

    # 體力條：以 ENERGY_BAR_REF 為滿格基準，儲備超過就滿條、看數字
    frac = min(1.0, game.energy / float(ENERGY_BAR_REF))
    color = ENERGY_OK if frac > 0.5 else (ENERGY_MID if frac > 0.25 else ENERGY_LOW)
    bar = pygame.Rect(14, TOP_BAR - 20, WIDTH - 28, 12)
    pygame.draw.rect(screen, (40, 44, 50), bar, border_radius=6)
    if game.energy > 0:
        fill = bar.copy()
        fill.width = max(6, int(bar.width * frac))
        pygame.draw.rect(screen, color, fill, border_radius=6)
    txt = small.render("體力 %d" % game.energy, True, TEXT)
    screen.blit(txt, (bar.centerx - txt.get_width() // 2,
                      bar.centery - txt.get_height() // 2 - 1))

    # AI 當下的決策模式（自動模式開著才顯示）
    if mode_text:
        mt = small.render("AI：" + mode_text, True, TEXT)
        screen.blit(mt, (bar.x + 8, bar.centery - mt.get_height() // 2 - 1))


def draw_algo_menu(screen, algo_idx, small):
    """「尋路」下拉選單：目前選項打勾，滑鼠掃過的選項亮底。"""
    mouse = pygame.mouse.get_pos()
    box = algo_option_rects()[0].unionall(algo_option_rects()[1:]).inflate(0, 8)
    pygame.draw.rect(screen, (36, 40, 47), box, border_radius=8)
    pygame.draw.rect(screen, (80, 90, 105), box, 1, border_radius=8)
    for i, r in enumerate(algo_option_rects()):
        if r.collidepoint(mouse):
            pygame.draw.rect(screen, (62, 84, 118), r.inflate(-6, -2),
                             border_radius=6)
        mark = "✓ " if i == algo_idx else "　 "
        label = small.render(mark + AUTO_ALGOS[i][0], True,
                             TEXT if i == algo_idx else TEXT_DIM)
        screen.blit(label, (r.x + 12, r.centery - label.get_height() // 2))


def draw_center_text(screen, lines, font, small):
    mask = pygame.Surface((WIDTH, HEIGHT - TOP_BAR), pygame.SRCALPHA)
    mask.fill((10, 12, 15, 170))
    screen.blit(mask, (0, TOP_BAR))
    y = TOP_BAR + (HEIGHT - TOP_BAR) // 2 - len(lines) * 26
    for text, big in lines:
        f = font if big else small
        surf = f.render(text, True, TEXT if big else TEXT_DIM)
        screen.blit(surf, ((WIDTH - surf.get_width()) // 2, y))
        y += surf.get_height() + (14 if big else 8)


# ---------------------------------------------------------------- 主程式

def main():
    pygame.init()
    pygame.key.stop_text_input()   # 關掉文字輸入模式，中文輸入法不會攔走按鍵
    pygame.display.set_caption("貪吃蛇：體力與地形")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = load_font(26, bold=True)
    small = load_font(16)
    sounds = load_sounds()
    particles = Particles()

    def play(name):
        if name in sounds:
            sounds[name].play()

    game = Game()
    best = load_hiscore()
    auto = False
    algo_idx = 0
    algo_open = False              # 「尋路」下拉選單是否展開
    acc = 0.0

    # 行為記錄的狀態
    ai_mode = None        # AI 目前的決策模式（追紅蘋果/跟尾巴…）
    mode_since = 0        # 這個模式從第幾步開始
    game_no = [0]         # 第幾局（JSONL 用來分局）

    def log_game_start():
        game_no[0] += 1
        log_line("")
        log_line("═══ 新的一局　%s　模式：%s ═══" % (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ("自動(%s)" % AUTO_ALGOS[algo_idx][0]) if auto else "手動"),
            data={"ev": "start", "game": game_no[0], "auto": auto,
                  "algo": AUTO_ALGOS[algo_idx][0]})

    log_game_start()

    while True:
        dt_ms = clock.tick(60)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_hiscore(best)
                pygame.quit()
                return 0
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if algo_open:
                    # 選單展開中：點到選項就切換，點其他地方只收起選單
                    algo_open = False
                    for i, r in enumerate(algo_option_rects()):
                        if r.collidepoint(event.pos) and i != algo_idx:
                            algo_idx = i
                            log_line("[步 %4d] 切換尋路演算法 → %s" % (
                                game.steps, AUTO_ALGOS[algo_idx][0]),
                                data={"ev": "algo", "step": game.steps,
                                      "algo": AUTO_ALGOS[algo_idx][0]})
                            ai_mode = None
                elif AUTO_BTN.collidepoint(event.pos):
                    auto = not auto
                    log_line("[步 %4d] %s自動模式（%s）" % (
                        game.steps, "開啟" if auto else "關閉",
                        AUTO_ALGOS[algo_idx][0]),
                        data={"ev": "auto", "step": game.steps, "on": auto,
                              "algo": AUTO_ALGOS[algo_idx][0]})
                    ai_mode = None
                elif ALGO_BTN.collidepoint(event.pos):
                    algo_open = True
                elif PAUSE_BTN.collidepoint(event.pos) and game.alive:
                    game.paused = not game.paused
            if event.type == pygame.KEYDOWN:
                sc = event.scancode
                if event.key == pygame.K_ESCAPE:
                    save_hiscore(best)
                    pygame.quit()
                    return 0
                if sc == SCAN_AUTO:
                    auto = not auto
                    log_line("[步 %4d] %s自動模式（%s）" % (
                        game.steps, "開啟" if auto else "關閉",
                        AUTO_ALGOS[algo_idx][0]),
                        data={"ev": "auto", "step": game.steps, "on": auto,
                              "algo": AUTO_ALGOS[algo_idx][0]})
                    ai_mode = None
                elif sc == SCAN_ALGO:
                    algo_open = False
                    algo_idx = (algo_idx + 1) % len(AUTO_ALGOS)
                    log_line("[步 %4d] 切換尋路演算法 → %s" % (
                        game.steps, AUTO_ALGOS[algo_idx][0]),
                        data={"ev": "algo", "step": game.steps,
                              "algo": AUTO_ALGOS[algo_idx][0]})
                    ai_mode = None
                elif sc in SCAN_DIR and game.alive and not game.paused:
                    if not auto:
                        game.turn(SCAN_DIR[sc])
                elif sc in SCAN_PAUSE and game.alive:
                    game.paused = not game.paused
                elif sc in SCAN_RESTART or (not game.alive and sc in SCAN_PAUSE):
                    game.reset()
                    particles.items.clear()
                    acc = 0.0
                    ai_mode = None
                    log_game_start()

        acc += dt_ms
        interval = 1000.0 / game.fps
        while acc >= interval and game.alive and not game.paused:
            acc -= interval
            if auto:
                d, mode = AUTO_ALGOS[algo_idx][1](game)
                if mode != ai_mode:            # 決策模式改變才記，避免洗版
                    mdata = {"ev": "mode", "step": game.steps, "to": mode,
                             "from": ai_mode,
                             "prev_steps": (game.steps - mode_since
                                            if ai_mode is not None else 0),
                             "energy": game.energy, "len": len(game.snake),
                             "score": game.score,
                             "algo": AUTO_ALGOS[algo_idx][0]}
                    if ai_mode is not None:
                        log_line("[步 %4d] 模式 %s → %s（前者持續 %d 步，體力 %d，長度 %d）"
                                 % (game.steps, ai_mode, mode,
                                    game.steps - mode_since, game.energy,
                                    len(game.snake)), data=mdata)
                    else:
                        log_line("[步 %4d] 模式 %s（體力 %d）"
                                 % (game.steps, mode, game.energy), data=mdata)
                    ai_mode = mode
                    mode_since = game.steps
                if d:
                    game.turn(d)
            for ev in game.step():
                snap = {"step": game.steps, "score": game.score,
                        "energy": game.energy,
                        "len": len(game.snake) + game.grow}
                if ev == "eat":
                    play("eat")
                    particles.burst(game.snake[0], FOOD)
                    log_line("[步 %4d] 吃紅蘋果 +10　分數 %d　體力 %d　長度 %d"
                             % (game.steps, game.score, game.energy,
                                len(game.snake) + game.grow),
                             data=dict(snap, ev="eat", kind="red"))
                elif ev == "gold":
                    play("gold")
                    particles.burst(game.snake[0], GOLD, 24)
                    log_line("[步 %4d] 吃金蘋果 +50　分數 %d　體力 %d"
                             % (game.steps, game.score, game.energy),
                             data=dict(snap, ev="eat", kind="gold"))
                elif ev == "blue":
                    play("blue")
                    particles.burst(game.snake[0], BLUE, 20)
                    log_line("[步 %4d] 吃藍蘋果 -20分 減重3節　分數 %d　體力 %d　長度 %d"
                             % (game.steps, game.score, game.energy,
                                len(game.snake) + game.grow),
                             data=dict(snap, ev="eat", kind="blue"))
                elif ev == "portal":
                    play("portal")
                    particles.burst(game.snake[0], PORTAL, 16)
                    log_line("[步 %4d] 走傳送門 → %s" % (game.steps,
                                                        game.snake[0]),
                             data=dict(snap, ev="portal",
                                       to=list(game.snake[0])))
                elif ev == "elev":
                    play("portal")
                    particles.burst(game.snake[0], ELEV_COLOR, 16)
                    log_line("[步 %4d] 搭電梯 → %s層 %s"
                             % (game.steps,
                                "下" if game.snake[0][2] == 1 else "上",
                                game.snake[0][:2]),
                             data=dict(snap, ev="elev",
                                       to=list(game.snake[0])))
                elif ev == "gold_gone":
                    log_line("[步 %4d] 金蘋果逾時消失" % game.steps,
                             data=dict(snap, ev="expire", kind="gold"))
                elif ev == "blue_gone":
                    log_line("[步 %4d] 藍蘋果逾時消失" % game.steps,
                             data=dict(snap, ev="expire", kind="blue"))
                elif ev in ("die", "win"):
                    play("gold" if ev == "win" else "die")
                    particles.burst(game.snake[0], (200, 200, 200), 30)
                    if game.score > best:
                        best = game.score
                        save_hiscore(best)
                    tail_note = ""
                    if auto and ai_mode is not None:
                        tail_note = "　死時模式：%s（已持續 %d 步）" % (
                            ai_mode, game.steps - mode_since)
                    log_line("[步 %4d] ─── %s：%s　分數 %d　長度 %d　剩餘體力 %d%s"
                             % (game.steps,
                                "通關" if ev == "win" else "死亡",
                                "吃光全場" if ev == "win" else game.death_cause,
                                game.score, len(game.snake), game.energy,
                                tail_note),
                             data=dict(snap, ev=ev,
                                       cause="win" if ev == "win"
                                       else game.death_cause,
                                       auto=auto,
                                       algo=AUTO_ALGOS[algo_idx][0] if auto else None,
                                       last_mode=ai_mode if auto else None,
                                       last_mode_steps=(game.steps - mode_since)
                                       if auto and ai_mode else None))

        best = max(best, game.score)
        particles.update(dt_ms / 1000.0)

        screen.fill(BG_DARK)
        draw_board(screen, game)
        draw_layers_chrome(screen, small)
        draw_portals(screen, game, now)
        draw_rocks(screen, game)
        draw_items(screen, game, now)
        draw_snake(screen, game)
        particles.draw(screen)
        mode_text = None
        if auto and ai_mode is not None and game.alive:
            mode_text = "%s（%d步）" % (ai_mode, game.steps - mode_since)
        draw_bar(screen, game, best, auto, algo_idx, mode_text, font, small)

        if game.paused:
            draw_center_text(screen, [("暫停", True),
                                      ("按 空白鍵 繼續", False)], font, small)
        elif not game.alive:
            title = "通關了！" if game.win else "遊戲結束"
            cause = "" if game.win else "（%s）" % game.death_cause
            newbest = "★ 新紀錄！" if game.score >= best and game.score > 0 else ""
            draw_center_text(screen, [
                (title, True),
                ("%s分數 %d　　最高 %d　%s" % (cause and cause + "　",
                                              game.score, best, newbest), False),
                ("按 R / Enter / 空白鍵 重新開始，ESC 離開", False),
            ], font, small)

        if algo_open:                  # 下拉選單畫在最上層
            draw_algo_menu(screen, algo_idx, small)

        pygame.display.flip()


if __name__ == "__main__":
    sys.exit(main())
