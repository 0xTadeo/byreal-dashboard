#!/bin/bash
# ============================================================
# Byreal Dashboard — 一键启动脚本
# 用法: chmod +x start.sh && ./start.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  Byreal Ops Dashboard — Setup & Start"
echo "================================================"
echo ""

# --- 1. 检查 Python ---
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi
echo "✓ Python: $(python3 --version)"

# --- 2. 创建 data 目录 ---
mkdir -p data

# --- 3. 运行数据采集 ---
echo ""
echo ">>> 运行数据采集..."
python3 collect.py

# --- 4. 运行 Twitter 采集（如果可用） ---
echo ""
echo ">>> 运行 Twitter 采集..."
python3 collect_twitter.py 2>/dev/null || echo "  ⚠ Twitter 采集跳过（Playwright 未安装）"

# --- 5. 推送 Lark（如果配置了 webhook） ---
if [ -n "$LARK_WEBHOOK" ]; then
    echo ""
    echo ">>> 推送 Lark..."
    python3 push_lark.py
else
    echo ""
    echo "⚠ 未设置 LARK_WEBHOOK，跳过 Lark 推送"
    echo "  设置方法: export LARK_WEBHOOK='https://open.larksuite.com/open-apis/bot/v2/hook/xxx'"
fi

# --- 6. 启动 Web 服务器 ---
echo ""
echo "================================================"
echo "  启动 Web Dashboard"
echo "================================================"
echo ""
echo "  本地访问:   http://localhost:8080/dashboard/"
echo "  停止服务:   Ctrl+C"
echo ""

# 从项目根目录启动（这样 /data/latest/summary.json 路径能对上）
cd "$SCRIPT_DIR"
python3 -m http.server 8080
