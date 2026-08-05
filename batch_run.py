# -*- coding: utf-8 -*-
"""批量模式 —— 無視窗跑整局遊戲，定量對比各演算法。

    .venv/bin/python batch_run.py                      # 全部演算法各跑 30 局
    .venv/bin/python batch_run.py --games 100          # 局數
    .venv/bin/python batch_run.py --algos BFS,DIJ庫    # 只跑指定演算法（庫＝外部套件版）
    .venv/bin/python batch_run.py --seed 42            # 換一批地圖
    .venv/bin/python batch_run.py --max-steps 50000    # 步數上限（超過記為超時）
    .venv/bin/python batch_run.py --jobs 1             # 除錯用：關掉並行

並行：局與局互相獨立，用 multiprocessing 按「局」分發到多個 process
（預設 CPU 核數-1）。不能用 threading —— 純 Python 計算會被 GIL 卡住，
而且 Game 依賴全域 random，執行緒共用亂數狀態會毀掉可重現性；
每個 process 有自己的亂數狀態，run_one() 開局先 seed，種子互不干擾。

公平性：第 g 局固定用種子 seed+g，所以每個演算法都拿到同一張初始地圖與
同一串生成序列（開局後蛇走不同路，後續生成點會隨局面分岔 —— 規則使然）。
同參數重跑結果完全相同（演算法本身不用亂數，跟哪個 process 跑到無關）。

輸出：終端印統計表；每局明細附加寫入 批量結果.jsonl（一行一局，
含 run 欄位可分批），之後要畫圖或統計直接逐行 json.loads。
"""

import argparse
import datetime
import json
import multiprocessing
import os
import random
import statistics
import sys
import time

from environment import Game
from algorithms import AUTO_ALGOS

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_JSONL = os.path.join(_BASE_DIR, "批量結果.jsonl")

CAUSES = ("撞牆", "撞到石頭", "撞到自己", "體力耗盡", "超時")


def run_one(algo_fn, seed, max_steps):
    """無視窗跑一整局，回傳這局的統計。"""
    random.seed(seed)
    game = Game()
    t_decide = 0.0
    while game.alive and game.steps < max_steps:
        t0 = time.perf_counter()
        d, _mode = algo_fn(game)
        t_decide += time.perf_counter() - t0
        if d:
            game.turn(d)
        game.step()
    cause = ("通關" if game.win else
             game.death_cause if not game.alive else "超時")
    return {
        "seed": seed,
        "score": game.score,
        "steps": game.steps,
        "len": len(game.snake),
        "cause": cause,
        "decide_ms": t_decide / max(1, game.steps) * 1000,
    }


def _run_task(task):
    """worker 進程的入口：按名字查演算法（函式物件不用跨進程傳）。"""
    name, seed, max_steps = task
    fn = dict(AUTO_ALGOS)[name]
    return name, run_one(fn, seed, max_steps)


def pick_algos(spec):
    """把 --algos 的逗號清單對回 AUTO_ALGOS；「·」可省略（DIJ庫＝DIJ·庫）。"""
    if not spec:
        return AUTO_ALGOS
    lookup = {}
    for name, fn in AUTO_ALGOS:
        lookup[name] = (name, fn)
        lookup[name.replace("·", "")] = (name, fn)
    chosen = []
    for token in spec.split(","):
        token = token.strip()
        if token not in lookup:
            sys.exit("不認識的演算法：%s（可用：%s）" % (
                token, "、".join(name for name, _ in AUTO_ALGOS)))
        if lookup[token] not in chosen:
            chosen.append(lookup[token])
    return chosen


def main():
    ap = argparse.ArgumentParser(description="批量對比各演算法（無視窗）")
    ap.add_argument("--games", type=int, default=30, help="每個演算法跑幾局（預設 30）")
    ap.add_argument("--algos", default="", help="逗號分隔，如 BFS,DIJ庫（預設全部）")
    ap.add_argument("--seed", type=int, default=2026, help="地圖種子基底（預設 2026）")
    ap.add_argument("--max-steps", type=int, default=100000,
                    help="單局步數上限，超過記為超時（預設 100000）")
    ap.add_argument("--jobs", type=int,
                    default=max(1, (os.cpu_count() or 2) - 1),
                    help="並行 process 數（預設 CPU 核數-1；1＝不並行）")
    args = ap.parse_args()

    algos = pick_algos(args.algos)
    run_id = datetime.datetime.now().isoformat(timespec="seconds")
    print("批量模式：%d 個演算法 × %d 局　種子 %d　步數上限 %d　並行 %d" % (
        len(algos), args.games, args.seed, args.max_steps, args.jobs))

    # 所有 (演算法, 局) 攤平成一池任務，讓快慢演算法混著跑填滿核
    tasks = [(name, args.seed + g, args.max_steps)
             for name, _ in algos for g in range(args.games)]
    results = {name: [] for name, _ in algos}
    t0 = time.perf_counter()
    if args.jobs <= 1:
        stream = map(_run_task, tasks)
        pool = None
    else:
        pool = multiprocessing.Pool(args.jobs)
        stream = pool.imap_unordered(_run_task, tasks)
    # 邊跑邊落盤：每完成一局立刻 append 一行 jsonl（背景跑也能 tail 看進度）
    step = max(1, len(tasks) // 20)
    fh_out = None
    try:
        fh_out = open(RESULT_JSONL, "a", encoding="utf-8")
    except IOError:
        pass
    for done, (name, row) in enumerate(stream, 1):
        results[name].append(row)
        if fh_out:
            fh_out.write(json.dumps(dict(row, algo=name, run=run_id),
                                    ensure_ascii=False) + "\n")
            fh_out.flush()
        if sys.stdout.isatty():
            print("進度 %d/%d …" % (done, len(tasks)), end="\r", flush=True)
        elif done % step == 0 or done == len(tasks):
            print("進度 %d/%d（%d%%）　耗時 %.0fs" % (
                done, len(tasks), done * 100 // len(tasks),
                time.perf_counter() - t0), flush=True)
    if fh_out:
        fh_out.close()
    if pool is not None:
        pool.close()
        pool.join()
    elapsed = time.perf_counter() - t0

    print()
    header = "%-8s %6s %8s %6s %8s %8s %8s　%s" % (
        "演算法", "局數", "平均分", "最高分", "平均步數", "平均長度", "決策ms", "結局分佈")
    print(header)
    print("─" * 78)

    for name, _fn in algos:
        rows = sorted(results[name], key=lambda r: r["seed"])
        scores = [r["score"] for r in rows]
        dist = []
        for cause in ("通關",) + CAUSES:
            n = sum(1 for r in rows if r["cause"] == cause)
            if n:
                dist.append("%s×%d" % (cause, n))
        print("%-8s %6d %8.1f %6d %8.0f %8.1f %8.2f　%s" % (
            name, len(rows),
            statistics.mean(scores), max(scores),
            statistics.mean(r["steps"] for r in rows),
            statistics.mean(r["len"] for r in rows),
            statistics.mean(r["decide_ms"] for r in rows),
            " ".join(dist)))

    print()
    print("共 %d 局，耗時 %.1f 秒" % (len(tasks), elapsed))
    print("每局明細已附加寫入 %s（run=%s）" % (os.path.basename(RESULT_JSONL), run_id))


if __name__ == "__main__":
    main()
