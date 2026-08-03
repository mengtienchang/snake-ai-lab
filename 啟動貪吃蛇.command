#!/bin/bash
# 雙擊這個檔就會開啟貪吃蛇。pygame 裝在旁邊的 .venv 虛擬環境裡，不影響系統。
cd "$(dirname "$0")" || exit 1

if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python snake_game.py
fi

echo "找不到虛擬環境，正在建立並安裝 pygame（只需做這一次）…"
python3 -m venv .venv && .venv/bin/pip install pygame-ce && exec .venv/bin/python snake_game.py

echo "建立失敗，請手動執行："
echo "    python3 -m venv .venv && .venv/bin/pip install pygame-ce"
read -r -n 1
