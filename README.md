# Byreal Ops Dashboard

每日运营数据看板，数据来源：Byreal API / CoinGecko / DefiLlama / Twitter。

## 快速开始

```bash
# 1. 下载项目到 Mac Mini
cd ~/
# 将整个 byreal-dashboard 文件夹放到这里

# 2. 首次运行
cd byreal-dashboard
chmod +x start.sh setup_cron.sh
./start.sh

# 3. 浏览器打开
open http://localhost:8080/dashboard/
```

## 项目结构

```
byreal-dashboard/
├── collect.py           # 核心数据采集 (Byreal + CoinGecko + DefiLlama)
├── collect_twitter.py   # Twitter 数据采集 (Playwright / fallback)
├── push_lark.py         # Lark 每日摘要推送
├── start.sh             # 一键启动（采集 + 推送 + 服务器）
├── setup_cron.sh        # 配置每日定时任务 + 开机启动
├── dashboard/
│   └── index.html       # 单文件 React 看板
└── data/
    ├── latest -> YYYY-MM-DD/   # 软链接到最新数据
    └── YYYY-MM-DD/
        ├── pools_raw.json      # Byreal API 原始响应
        ├── market.json         # 行情数据
        ├── competitors.json    # 竞品数据
        ├── twitter.json        # Twitter 数据
        └── summary.json        # 聚合摘要（看板读取）
```

## 配置

### Lark Webhook

```bash
# 设置环境变量（沿用 Byreal Daily 的 webhook）
export LARK_WEBHOOK='https://open.larksuite.com/open-apis/bot/v2/hook/你的webhook'

# 或直接传参
python3 push_lark.py --webhook 'https://...'
```

### Twitter 采集

安装 Playwright（可选，不装也能运行，只是没 Twitter 数据）:

```bash
pip3 install playwright
playwright install chromium
```

添加/删除追踪账号：编辑 `collect_twitter.py` 中的 `ACCOUNTS` 字典。

### 外网访问

```bash
# 安装 Cloudflare Tunnel
brew install cloudflare/cloudflare/cloudflared

# 启动隧道
cloudflared tunnel --url http://localhost:8080

# 后台运行
nohup cloudflared tunnel --url http://localhost:8080 > data/tunnel.log 2>&1 &
```

## 定时任务

```bash
# 一键配置 cron + 开机启动
./setup_cron.sh

# 手动添加 cron（每天北京时间 09:00）
crontab -e
# 添加:
# 0 1 * * * cd ~/byreal-dashboard && python3 collect.py >> data/cron.log 2>&1 && LARK_WEBHOOK='...' python3 push_lark.py >> data/cron.log 2>&1
```

## 看板模块

| 模块 | 内容 |
|------|------|
| **市场行情栏** | SOL/BTC/ETH 价格 + 24h 变化 + Fear & Greed |
| **每日行动项** | 基于规则的自动预警和建议 |
| **平台 KPI** | TVL / 交易量 / 手续费 / 收入 / 活跃池 |
| **业务线分布** | xStocks / 黄金RWA / 主流对 / Meme 分类统计 + 饼图 |
| **xStocks 专区** | 所有 xStocks 池详情 + 7d 走势 |
| **池子排行** | Top TVL / Top 交易量 / Top Fee/TVL / Top APR |
| **竞品对比** | Raydium / Meteora / Orca / PumpSwap 横向对比 |

## 预警规则

| 触发条件 | 预警级别 | 建议动作 |
|---------|---------|---------|
| SOL 24h > ±10% | 🟢/🟠 | 发推 bbSOL 质押/抄底 |
| Fear & Greed < 20 | 🟢 | "逆市机会"内容 |
| Fear & Greed > 80 | 🟠 | "注意风险"提醒 |
| xStocks 24h > ±5% | 🟢/🟠 | 关联新闻推文 |
| 池子 APR > 500% | 🟠 | 异常监控 |
| 激励 < 7 天到期 | 🔴 | 提醒团队续期 |
| TVL 日跌 > 5% | 🔴 | 排查原因 |
| 新池上线 | 🟢 | 准备介绍推文 |

## 技术说明

- **零依赖**: Python 3 标准库即可运行核心采集（无需 pip install）
- **Twitter 采集**: 需要 Playwright（可选）
- **看板**: 纯静态 HTML + React CDN，无需 Node.js
- **存储**: JSON 文件，永久保留，每天 ~500KB
- **刷新**: 看板自动每 5 分钟重新加载数据
