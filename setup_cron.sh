#!/bin/bash
# ============================================================
# Byreal Dashboard — Cron 自动化配置
# 用法: chmod +x setup_cron.sh && ./setup_cron.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "================================================"
echo "  配置 Cron 定时任务"
echo "================================================"
echo ""

# 检查是否已有 cron
EXISTING=$(crontab -l 2>/dev/null | grep "byreal-dashboard" || true)
if [ -n "$EXISTING" ]; then
    echo "⚠ 已存在 Byreal Dashboard cron 任务:"
    echo "  $EXISTING"
    echo ""
    read -p "是否覆盖？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消"
        exit 0
    fi
    # 删除旧任务
    crontab -l 2>/dev/null | grep -v "byreal-dashboard" | crontab -
fi

# Webhook
read -p "Lark Webhook URL (回车跳过): " WEBHOOK

# 构建 cron 命令
CRON_CMD="cd $SCRIPT_DIR && python3 collect.py >> data/cron.log 2>&1"
if [ -n "$WEBHOOK" ]; then
    CRON_CMD="cd $SCRIPT_DIR && python3 collect.py >> data/cron.log 2>&1 && LARK_WEBHOOK='$WEBHOOK' python3 push_lark.py >> data/cron.log 2>&1"
fi

# 每天 UTC 01:00 (北京时间 09:00) 运行
CRON_LINE="0 1 * * * $CRON_CMD # byreal-dashboard"

# 添加到 crontab
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

echo ""
echo "✅ Cron 任务已添加:"
echo "  $CRON_LINE"
echo ""
echo "📋 说明:"
echo "  - 每天 UTC 01:00（北京时间 09:00）自动运行"
echo "  - 日志: $SCRIPT_DIR/data/cron.log"
echo "  - 查看 cron: crontab -l"
echo "  - 编辑 cron: crontab -e"
echo ""

# Web 服务器 (launchd on macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "================================================"
    echo "  配置 macOS 开机启动 Web 服务"
    echo "================================================"

    PLIST="$HOME/Library/LaunchAgents/com.byreal.dashboard.plist"
    cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.byreal.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>http.server</string>
        <string>8080</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/data/server.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/data/server.log</string>
</dict>
</plist>
EOF

    launchctl load "$PLIST" 2>/dev/null || true
    echo "✅ Web 服务已配置为开机启动"
    echo "  访问: http://localhost:8080/dashboard/"
    echo "  停止: launchctl unload $PLIST"
fi

echo ""
echo "================================================"
echo "  Cloudflare Tunnel (外网访问)"
echo "================================================"
echo ""
echo "安装:"
echo "  brew install cloudflare/cloudflare/cloudflared"
echo ""
echo "一键启动外网隧道:"
echo "  cloudflared tunnel --url http://localhost:8080"
echo ""
echo "这会生成一个公网 URL，如:"
echo "  https://xxxx-xxxx-xxxx.trycloudflare.com/dashboard/"
echo ""
echo "常驻运行（后台）:"
echo "  nohup cloudflared tunnel --url http://localhost:8080 > data/tunnel.log 2>&1 &"
