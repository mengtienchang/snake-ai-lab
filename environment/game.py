# -*- coding: utf-8 -*-
"""Game 類 —— 遊戲規則本體。

只管規則：移動、碰撞、體力、物件生成與倒數。不畫畫面、不放音效、不記錄，
所以可以無視窗跑（測試、批量模擬、之後接 RL 都靠這個性質）。
step() 回傳事件列表（eat/gold/blue/portal/…_gone/die/win），由外層自行反應。
"""

import random

from .config import (
    GRID_W, GRID_H, DIRS, RIGHT, OPPOSITE,
    START_FPS, MAX_FPS, SPEEDUP_EVERY,
    ENABLE_ROCKS, ENABLE_ROUGH, ENABLE_PORTALS,
    ENABLE_LAYERS, ELEVATORS,
    GOLD_EVERY, GOLD_TTL, BLUE_EVERY, BLUE_TTL,
    PORTAL_EVERY, PORTAL_TTL, ROCK_EVERY, ROCK_SAFE_DIST,
    ENERGY_START, ENERGY_MAX, ENERGY_RED, ENERGY_GOLD, ENERGY_BLUE,
    COST_NORMAL, COST_ROUGH,
    BLUE_SCORE_PENALTY, BLUE_SHRINK,
    ROUGH_BLOBS, ROUGH_BLOB_SIZE,
)


class Game(object):
    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy = GRID_W // 2, GRID_H // 2
        if ENABLE_LAYERS:                       # 雙層：座標帶層號 (x, y, z)
            self.snake = [(cx - i, cy, 0) for i in range(3)]
        else:
            self.snake = [(cx - i, cy) for i in range(3)]
        self.direction = RIGHT
        self.pending = RIGHT
        self.grow = 0
        self.obstacles = set()
        self.rough = self._gen_rough()      # 碎石地
        self.gold = None
        self.gold_left = 0
        self.blue = None
        self.blue_left = 0
        self.portals = None                 # (posA, posB) 或 None
        self.portal_left = 0
        self.energy = ENERGY_START
        self.food = None
        self.food = self.spawn_empty()
        self.score = 0
        self.eaten = 0
        self.steps = 0            # 這一局走了幾步（行為記錄用）
        self.fps = START_FPS
        self.alive = True
        self.paused = False
        self.win = False
        self.death_cause = ""

    # ---- 地形 ----

    def _gen_rough(self):
        """隨機長幾塊碎石地，避開蛇的起始列。"""
        if not ENABLE_ROUGH:
            return set()
        rough = set()
        start_row = GRID_H // 2
        for _ in range(ROUGH_BLOBS):
            x = random.randrange(GRID_W)
            y = random.randrange(GRID_H)
            size = random.randint(*ROUGH_BLOB_SIZE)
            cell = (x, y)
            for _ in range(size):
                if abs(cell[1] - start_row) > 1:
                    rough.add(cell)
                dx, dy = random.choice(DIRS)
                cell = (max(0, min(GRID_W - 1, cell[0] + dx)),
                        max(0, min(GRID_H - 1, cell[1] + dy)))
        return rough

    def step_cost(self, pos):
        return COST_ROUGH if pos in self.rough else COST_NORMAL

    # ---- 產生物件 ----

    def occupied(self):
        cells = set(self.snake) | self.obstacles
        for it in (self.food, self.gold, self.blue):
            if it:
                cells.add(it)
        if self.portals:
            cells.update(self.portals)
        return cells

    def spawn_empty(self, min_dist_from_head=0):
        head = self.snake[0]
        taken = self.occupied()
        if ENABLE_LAYERS:
            # 物品只刷在上層（z=0），下層是純逃生空間；電梯格保持淨空。
            # 蛇頭在下層時，上層任何格都視為離頭夠遠。
            empty = [(x, y, 0)
                     for x in range(GRID_W) for y in range(GRID_H)
                     if (x, y, 0) not in taken and (x, y) not in ELEVATORS
                     and (head[2] != 0
                          or abs(x - head[0]) + abs(y - head[1]) >= min_dist_from_head)]
        else:
            empty = [(x, y) for x in range(GRID_W) for y in range(GRID_H)
                     if (x, y) not in taken
                     and abs(x - head[0]) + abs(y - head[1]) >= min_dist_from_head]
        return random.choice(empty) if empty else None

    def maybe_spawn_extras(self):
        if ENABLE_ROCKS and self.eaten % ROCK_EVERY == 0:
            rock = self.spawn_empty(ROCK_SAFE_DIST)
            if rock:
                self.obstacles.add(rock)
        if self.eaten % GOLD_EVERY == 0 and self.gold is None:
            self.gold = self.spawn_empty(2)
            self.gold_left = GOLD_TTL if self.gold else 0
        if self.eaten % BLUE_EVERY == 0 and self.blue is None:
            self.blue = self.spawn_empty(2)
            self.blue_left = BLUE_TTL if self.blue else 0
        if ENABLE_PORTALS and self.eaten % PORTAL_EVERY == 0 and self.portals is None:
            a = self.spawn_empty(3)
            if a:
                # 兩個門距離要夠遠才有捷徑的意義
                taken = self.occupied() | {a}
                far = [(x, y) for x in range(GRID_W) for y in range(GRID_H)
                       if (x, y) not in taken
                       and abs(x - a[0]) + abs(y - a[1]) >= 10]
                if far:
                    self.portals = (a, random.choice(far))
                    self.portal_left = PORTAL_TTL

    # ---- 每一步 ----

    def turn(self, new_dir):
        if new_dir != OPPOSITE[self.direction]:
            self.pending = new_dir

    def _die(self, cause):
        self.alive = False
        self.death_cause = cause
        return ["die"]

    def step(self):
        """走一步，回傳事件列表：eat/gold/blue/portal/…_gone/die/win。"""
        if not self.alive or self.paused:
            return []
        events = []
        self.steps += 1
        self.direction = self.pending
        hx, hy = self.snake[0][0], self.snake[0][1]
        dx, dy = self.direction
        if ENABLE_LAYERS:
            new_head = (hx + dx, hy + dy, self.snake[0][2])
        else:
            new_head = (hx + dx, hy + dy)

        # 限時物件倒數
        for attr, left_attr, gone in (("gold", "gold_left", "gold_gone"),
                                      ("blue", "blue_left", "blue_gone")):
            if getattr(self, attr) is not None:
                setattr(self, left_attr, getattr(self, left_attr) - 1)
                if getattr(self, left_attr) <= 0:
                    setattr(self, attr, None)
                    events.append(gone)
        if self.portals is not None:
            self.portal_left -= 1
            if self.portal_left <= 0:
                self.portals = None
                events.append("portal_gone")

        # 撞牆 / 石頭
        if not (0 <= new_head[0] < GRID_W and 0 <= new_head[1] < GRID_H):
            return events + self._die("撞牆")
        if new_head in self.obstacles:
            return events + self._die("撞到石頭")

        # 電梯：踏上角格就到另一層的同位置角格（之後照常前進）
        if ENABLE_LAYERS and (new_head[0], new_head[1]) in ELEVATORS:
            new_head = (new_head[0], new_head[1], 1 - new_head[2])
            events.append("elev")
            # 出電梯自動轉向：直行會出界就掰到唯一合法的垂直出口
            # （角落只有一個垂直方向在界內，手感像被電梯沿牆彈出去）
            nx, ny = new_head[0] + dx, new_head[1] + dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                for tdx, tdy in ((dy, dx), (-dy, -dx)):
                    if (0 <= new_head[0] + tdx < GRID_W
                            and 0 <= new_head[1] + tdy < GRID_H):
                        self.direction = self.pending = (tdx, tdy)
                        break

        # 傳送門：踏進一邊，從另一邊出來（出口被擋就當普通格子）
        if self.portals and new_head in self.portals:
            other = self.portals[1] if new_head == self.portals[0] else self.portals[0]
            exit_cell = (other[0] + dx, other[1] + dy)
            blocked = (not (0 <= exit_cell[0] < GRID_W and 0 <= exit_cell[1] < GRID_H)
                       or exit_cell in self.obstacles or exit_cell in self.snake)
            if not blocked:
                new_head = exit_cell
                events.append("portal")

        # 撞自己
        eats = new_head in (self.food, self.gold, self.blue)
        body = self.snake if (eats or self.grow > 0) else self.snake[:-1]
        if new_head in body:
            return events + self._die("撞到自己")

        # 體力：踏進去那格的地形決定消耗
        self.energy -= self.step_cost(new_head)
        if self.energy <= 0:
            self.energy = 0
            return events + self._die("體力耗盡")

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 10
            self.eaten += 1
            self.grow += 1
            self.energy = min(ENERGY_MAX, self.energy + ENERGY_RED)
            events.append("eat")
            if self.eaten % SPEEDUP_EVERY == 0 and self.fps < MAX_FPS:
                self.fps += 1
            self.maybe_spawn_extras()
            self.food = self.spawn_empty()
            if self.food is None:
                self.win = True
                self.alive = False
                events.append("win")
        elif new_head == self.gold:
            self.score += 50
            self.grow += 3
            self.energy = min(ENERGY_MAX, self.energy + ENERGY_GOLD)
            self.gold = None
            events.append("gold")
        elif new_head == self.blue:
            self.score = max(0, self.score - BLUE_SCORE_PENALTY)
            self.energy = min(ENERGY_MAX, self.energy + ENERGY_BLUE)
            self.blue = None
            # 身體 -3 節（保底 3 節），先抵掉還沒長出來的
            shrink = BLUE_SHRINK
            take = min(shrink, self.grow)
            self.grow -= take
            shrink -= take
            for _ in range(shrink):
                if len(self.snake) > 3:
                    self.snake.pop()
            events.append("blue")

        if self.grow > 0:
            self.grow -= 1
        else:
            self.snake.pop()
        return events
