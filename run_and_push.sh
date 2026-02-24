#!/bin/bash
# Byreal Dashboard — 采集数据 + git push 到 Streamlit Cloud
# 用法: 由 launchd 定时调用

set -e
cd "$(dirname "$0")"

LOG="data/cron.log"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

# 采集数据
/usr/bin/python3 collect.py >> "$LOG" 2>&1

# Git commit + push
if git diff --quiet && git diff --cached --quiet; then
    echo "No changes to commit" >> "$LOG"
else
    git add -A
    git commit -m "auto: data update $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
    git push >> "$LOG" 2>&1
    echo "✓ Pushed to GitHub" >> "$LOG"
fi
