#!/usr/bin/env python3
"""
Byreal Dashboard — 每日数据采集脚本
用法: python3 collect.py
建议通过 cron 每日 09:00 UTC 运行
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 导入新增的采集模块
try:
    from collect_x_trends import fetch_x_trends
    from collect_reddit import fetch_reddit_hot
except ImportError:
    print("[WARN] 无法导入 X/Reddit 采集模块，将跳过")
    fetch_x_trends = None
    fetch_reddit_hot = None

# ============================================================
# 配置
# ============================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

BYREAL_API = "https://api2.byreal.io/byreal/api/dex/v2/pools/info/list?page=1&pageSize=500"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=solana,bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
FNG_API = "https://api.alternative.me/fng/?limit=1"
DEFILLAMA_BASE = "https://api.llama.fi"

COMPETITORS = ["raydium", "meteora", "orca", "pumpswap"]

# 分类规则
XSTOCK_CATEGORY = 32
GOLD_KEYWORDS = ["XAUt"]
MAJOR_SYMBOLS = {"SOL", "WETH", "WBTC", "BTC", "ETH", "Wrapped SOL", "Wrapped Ether"}
STABLE_SYMBOLS = {"USDC", "USDT", "USD1", "DAI"}


# ============================================================
# 工具函数
# ============================================================
def fetch_json(url, timeout=30, retries=2):
    """HTTP GET → JSON，带重试"""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Byreal-Dashboard/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries:
                print(f"    重试 {attempt+1}/{retries}: {e}")
                time.sleep(2)
            else:
                print(f"    [ERROR] {url}: {e}")
                return None


def fmt_usd(val):
    """格式化美元"""
    if val >= 1_000_000_000:
        return f"${val/1e9:.2f}B"
    if val >= 1_000_000:
        return f"${val/1e6:.2f}M"
    if val >= 1_000:
        return f"${val/1e3:.1f}K"
    return f"${val:.0f}"


# ============================================================
# 池子分类
# ============================================================
def classify_pool(pool):
    base_sym = pool.get("baseMint", {}).get("mintInfo", {}).get("symbol", "")
    quote_sym = pool.get("quoteMint", {}).get("mintInfo", {}).get("symbol", "")
    category = pool.get("category", 0)

    # xStocks
    if category == XSTOCK_CATEGORY:
        return "xStocks"
    for sym in (base_sym, quote_sym):
        if sym.endswith("x") and len(sym) >= 3 and sym[:-1].isupper():
            return "xStocks"

    # Gold / RWA
    for kw in GOLD_KEYWORDS:
        if kw in base_sym or kw in quote_sym:
            return "Gold_RWA"

    # Stablecoin pair
    if base_sym in STABLE_SYMBOLS and quote_sym in STABLE_SYMBOLS:
        return "Stablecoin"

    # Major pair
    if base_sym in MAJOR_SYMBOLS or quote_sym in MAJOR_SYMBOLS:
        return "Major"

    return "Other"


# ============================================================
# 数据处理
# ============================================================
def process_pools(raw):
    records = raw.get("result", {}).get("data", {}).get("records", [])
    total_count = raw.get("result", {}).get("data", {}).get("total", 0)

    totals = {"tvl": 0, "vol24h": 0, "vol7d": 0, "fee24h": 0, "fee7d": 0}
    active = 0
    biz = {}
    pools = []

    for p in records:
        tvl = float(p.get("tvl") or 0)
        v24 = float(p.get("volumeUsd24h") or 0)
        v7d = float(p.get("volumeUsd7d") or 0)
        f24 = float(p.get("feeUsd24h") or 0)
        f7d = float(p.get("feeUsd7d") or 0)
        apr = float(p.get("feeApr24h") or 0)
        ftv = float(p.get("feeTvl1d") or 0)

        totals["tvl"] += tvl
        totals["vol24h"] += v24
        totals["vol7d"] += v7d
        totals["fee24h"] += f24
        totals["fee7d"] += f7d
        if v24 > 0:
            active += 1

        line = classify_pool(p)
        if line not in biz:
            biz[line] = {"tvl": 0, "vol24h": 0, "fee24h": 0, "count": 0}
        biz[line]["tvl"] += tvl
        biz[line]["vol24h"] += v24
        biz[line]["fee24h"] += f24
        biz[line]["count"] += 1

        base_info = p.get("baseMint", {}).get("mintInfo", {})
        quote_info = p.get("quoteMint", {}).get("mintInfo", {})
        name = f"{base_info.get('symbol', '?')}-{quote_info.get('symbol', '?')}"

        # 激励信息
        reward = None
        for r in p.get("rewards", []):
            token_info = r.get("token", {}).get("mintInfo", {})
            reward = {
                "symbol": token_info.get("symbol", ""),
                "apr": float(r.get("apr") or 0),
                "endTs": r.get("endTimestamp", 0),
                "dailyAmount": r.get("dailyAmountDisplay") or r.get("dailyMaxAmount", "0"),
            }
            break

        pools.append({
            "addr": p.get("poolAddress", ""),
            "name": name,
            "baseSym": base_info.get("symbol", ""),
            "quoteSym": quote_info.get("symbol", ""),
            "baseLogo": base_info.get("logoURI", ""),
            "quoteLogo": quote_info.get("logoURI", ""),
            "cat": p.get("category", 0),
            "biz": line,
            "tvl": tvl,
            "v1h": float(p.get("volumeUsd1h") or 0),
            "v24h": v24,
            "v7d": v7d,
            "f24h": f24,
            "f7d": f7d,
            "apr": apr,
            "ftv": ftv,
            "px": float(p.get("price") or 0),
            "pc1h": float(p.get("priceChange1h") or 0),
            "pc1d": float(p.get("priceChange1d") or 0),
            "pc7d": float(p.get("priceChange7d") or 0),
            "bonus": float(p.get("totalBonus") or 0),
            "reward": reward,
            "kline7d": [float(x) for x in p.get("kline7d", [])],
            "kline1d": [float(x) for x in p.get("kline1d", [])],
        })

    # 排行榜
    valid = [p for p in pools if p["tvl"] > 500]
    rankings = {
        "topTvl": sorted(pools, key=lambda x: x["tvl"], reverse=True)[:15],
        "topVol": sorted(pools, key=lambda x: x["v24h"], reverse=True)[:15],
        "topFtv": sorted(valid, key=lambda x: x["ftv"], reverse=True)[:15],
        "topApr": sorted(valid, key=lambda x: x["apr"], reverse=True)[:15],
    }

    xstocks = sorted([p for p in pools if p["biz"] == "xStocks"], key=lambda x: x["tvl"], reverse=True)

    return {
        "platform": {
            "tvl": totals["tvl"],
            "vol24h": totals["vol24h"],
            "vol7d": totals["vol7d"],
            "fee24h": totals["fee24h"],
            "fee7d": totals["fee7d"],
            "rev24h": totals["fee24h"] * 0.12,
            "active": active,
            "total": total_count,
        },
        "bizLines": biz,
        "rankings": rankings,
        "xStocks": xstocks,
        "pools": pools,
    }


# ============================================================
# 预警引擎
# ============================================================
def generate_alerts(summary, market, yesterday):
    alerts = []

    # SOL 大幅波动
    sol_chg = market.get("sol", {}).get("change24h", 0) or 0
    if abs(sol_chg) > 10:
        d = "暴涨" if sol_chg > 0 else "暴跌"
        alerts.append({"lv": "green" if sol_chg > 0 else "orange", "cat": "market",
                        "msg": f"SOL 24h {d} {sol_chg:+.1f}%，准备相关营销内容"})

    # Fear & Greed
    fng = market.get("fearGreed", {}).get("value", 50) or 50
    if fng < 20:
        alerts.append({"lv": "green", "cat": "market", "msg": f"Fear & Greed = {fng}（极度恐惧），准备'逆市机会'内容"})
    elif fng > 80:
        alerts.append({"lv": "orange", "cat": "market", "msg": f"Fear & Greed = {fng}（极度贪婪），提醒'注意风险'"})

    # xStocks 大幅波动
    for p in summary.get("xStocks", []):
        chg = p.get("pc1d", 0)
        if abs(chg) > 0.05:
            d = "涨" if chg > 0 else "跌"
            alerts.append({"lv": "green" if chg > 0 else "orange", "cat": "xstocks",
                            "msg": f"{p['name']} 24h {d} {abs(chg)*100:.1f}%，建议发推关联相关新闻"})

    # 高 APR
    for p in summary.get("pools", []):
        if p.get("apr", 0) > 5 and p.get("tvl", 0) > 1000:
            alerts.append({"lv": "orange", "cat": "pool",
                            "msg": f"{p['name']} APR {p['apr']*100:.0f}%，注意监控"})

    # 激励到期
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    for p in summary.get("pools", []):
        r = p.get("reward")
        if r and r.get("endTs"):
            days = (r["endTs"] - now_ms) / 86400000
            if 0 < days < 7:
                alerts.append({"lv": "red", "cat": "reward",
                                "msg": f"{p['name']} 激励 {days:.0f} 天后到期，提醒团队续期"})

    # 与昨天对比
    if yesterday:
        prev_tvl = yesterday.get("platform", {}).get("tvl", 0)
        curr_tvl = summary.get("platform", {}).get("tvl", 0)
        if prev_tvl > 0:
            chg = (curr_tvl - prev_tvl) / prev_tvl
            summary["platform"]["tvlChange"] = chg
            if chg < -0.05:
                alerts.append({"lv": "red", "cat": "platform",
                                "msg": f"平台 TVL 日环比下降 {abs(chg)*100:.1f}%，排查原因"})

        prev_vol = yesterday.get("platform", {}).get("vol24h", 0)
        curr_vol = summary.get("platform", {}).get("vol24h", 0)
        if prev_vol > 0:
            summary["platform"]["volChange"] = (curr_vol - prev_vol) / prev_vol

        # 新池检测
        prev_addrs = {p["addr"] for p in yesterday.get("pools", [])}
        for p in summary.get("pools", []):
            if p["addr"] not in prev_addrs and p["addr"]:
                alerts.append({"lv": "green", "cat": "newpool",
                                "msg": f"新池上线：{p['name']}，准备介绍推文"})

    return alerts


# ============================================================
# AI 总结
# ============================================================
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 尝试从 byreal-daily 的 .env 读取
if not ANTHROPIC_API_KEY:
    env_path = BASE_DIR.parent / "byreal-daily" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                ANTHROPIC_API_KEY = line.split("=", 1)[1].strip()
                break


def call_claude(prompt, max_tokens=1000):
    """调用 Claude API"""
    if not ANTHROPIC_API_KEY:
        return ""
    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"  [WARN] Claude API 失败: {e}")
        return ""


def generate_ai_summary(summary, market, comps, alerts):
    """生成两段 AI 总结"""
    p = summary["platform"]
    sol = market.get("sol", {})
    fng = market.get("fearGreed", {})

    # 构建数据摘要给 AI
    data_brief = f"""Byreal 平台数据（{datetime.now().strftime('%Y-%m-%d')}）:
- TVL: ${p['tvl']/1e6:.2f}M | 24h Vol: ${p['vol24h']/1e6:.2f}M | 24h Fee: ${p['fee24h']:,.0f}
- 活跃池: {p['active']}/{p['total']}
- TVL 日变化: {p.get('tvlChange', 'N/A')} | Vol 日变化: {p.get('volChange', 'N/A')}

业务线:
"""
    for k, v in summary.get("bizLines", {}).items():
        share = v["tvl"] / p["tvl"] * 100 if p["tvl"] > 0 else 0
        data_brief += f"  {k}: TVL ${v['tvl']/1e6:.2f}M ({share:.0f}%) | Vol ${v['vol24h']/1e6:.2f}M\n"

    data_brief += f"""
市场:
- SOL: ${sol.get('price',0):.2f} ({sol.get('change24h',0):+.1f}%)
- Fear & Greed: {fng.get('value', '?')} ({fng.get('label', '')})

竞品 TVL:
"""
    for slug, c in sorted(comps.items(), key=lambda x: x[1].get("tvl", 0), reverse=True):
        data_brief += f"  {c.get('name', slug)}: TVL ${c.get('tvl',0)/1e6:.1f}M | Vol ${c.get('vol24h',0)/1e6:.1f}M\n"

    data_brief += "\n预警:\n"
    for a in alerts:
        data_brief += f"  [{a['lv']}] {a['msg']}\n"

    # xStocks 行情
    xs = summary.get("xStocks", [])
    if xs:
        data_brief += "\nxStocks 行情:\n"
        for s in xs[:8]:
            chg = s.get("pc1d", 0)
            data_brief += f"  {s['name']}: ${s['px']:.2f} ({chg*100:+.1f}%) TVL ${s['tvl']/1e6:.2f}M\n"

    # --- 内部运营洞察 ---
    insight_prompt = f"""{data_brief}

你是 Byreal（Solana native DEX）的运营分析师。基于以上数据，写一段简短的运营洞察（3-5 句话），包含：
1. 今日平台整体表现判断
2. 最值得关注的 1-2 个机会或风险
3. 具体的运营行动建议

要求：直接、有观点、可执行。不要客套话。中文回答。"""

    # --- 对外平台快报 ---
    public_prompt = f"""{data_brief}

你是 Byreal（Solana native DEX）的内容运营。基于以上数据，写一段面向用户/客户的平台快报（3-4 句话），包含：
1. 平台亮点数据
2. 热门池子或 xStocks 机会
3. 适合发推/社群的正面信息

要求：积极专业、突出亮点、吸引用户参与。不要提风险预警。中文回答。"""

    insight = call_claude(insight_prompt)
    public = call_claude(public_prompt)

    if insight:
        print(f"  ✓ 运营洞察: {insight[:50]}...")
    if public:
        print(f"  ✓ 平台快报: {public[:50]}...")

    return {"insight": insight, "public": public}


# ============================================================
# 主流程
# ============================================================
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = DATA_DIR / today
    today_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*50}")
    print(f"  Byreal Dashboard Collector — {today}")
    print(f"{'='*50}\n")

    # --- 1. Byreal API ---
    print("[1/3] Byreal pool data...")
    raw = fetch_json(BYREAL_API, timeout=60)
    if not raw or raw.get("retCode") != 0:
        print("  ✗ Byreal API 请求失败，终止采集")
        sys.exit(1)
    with open(today_dir / "pools_raw.json", "w") as f:
        json.dump(raw, f, ensure_ascii=False)
    summary = process_pools(raw)
    p = summary["platform"]
    print(f"  ✓ {p['total']} pools | TVL {fmt_usd(p['tvl'])} | Vol24h {fmt_usd(p['vol24h'])}")

    # --- 2. Market data ---
    print("[2/3] Market data...")
    prices = fetch_json(COINGECKO_API) or {}
    fng = fetch_json(FNG_API)
    market = {
        "sol": {
            "price": (prices.get("solana") or {}).get("usd", 0),
            "change24h": (prices.get("solana") or {}).get("usd_24h_change", 0),
            "mcap": (prices.get("solana") or {}).get("usd_market_cap", 0),
        },
        "btc": {
            "price": (prices.get("bitcoin") or {}).get("usd", 0),
            "change24h": (prices.get("bitcoin") or {}).get("usd_24h_change", 0),
        },
        "eth": {
            "price": (prices.get("ethereum") or {}).get("usd", 0),
            "change24h": (prices.get("ethereum") or {}).get("usd_24h_change", 0),
        },
        "fearGreed": {
            "value": int(fng["data"][0]["value"]) if fng and fng.get("data") else 0,
            "label": (fng["data"][0].get("value_classification", "") if fng and fng.get("data") else ""),
        },
    }
    with open(today_dir / "market.json", "w") as f:
        json.dump(market, f, ensure_ascii=False)
    print(f"  ✓ SOL ${market['sol']['price']} | BTC ${market['btc']['price']} | F&G {market['fearGreed']['value']}")

    # --- 3. Competitors ---
    print("[3/3] Competitor data...")
    comps = {}
    for slug in COMPETITORS:
        d = fetch_json(f"{DEFILLAMA_BASE}/protocol/{slug}")
        if d:
            # 取 Solana 链的 TVL
            chain_tvls = d.get("currentChainTvls", {})
            tvl = chain_tvls.get("Solana", 0)
            if not tvl and d.get("tvl"):
                tvl = d["tvl"][-1].get("totalLiquidityUSD", 0) if d["tvl"] else 0
            comps[slug] = {"name": d.get("name", slug), "tvl": tvl}
        time.sleep(0.5)  # 避免限速

        vd = fetch_json(f"{DEFILLAMA_BASE}/summary/dexs/{slug}")
        if vd:
            comps.setdefault(slug, {})["vol24h"] = vd.get("total24h", 0)
            comps[slug]["vol7d"] = vd.get("total7d", 0)
        time.sleep(0.5)

    # 把 Byreal 自身也加入（用自己的实时数据）
    comps["byreal"] = {
        "name": "Byreal",
        "tvl": summary["platform"]["tvl"],
        "vol24h": summary["platform"]["vol24h"],
        "vol7d": summary["platform"]["vol7d"],
    }

    with open(today_dir / "competitors.json", "w") as f:
        json.dump(comps, f, ensure_ascii=False)
    print(f"  ✓ {len(comps)} protocols")

    # --- 4. 生成预警 ---
    yesterday_summary = None
    try:
        yd = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        yf = DATA_DIR / yd / "summary.json"
        if yf.exists():
            with open(yf) as f:
                yesterday_summary = json.load(f)
    except Exception:
        pass

    alerts = generate_alerts(summary, market, yesterday_summary)

    # --- 5. X/Twitter 热点 ---
    print("[4/7] X/Twitter 热点...")
    x_trends = []
    if fetch_x_trends:
        try:
            x_trends = fetch_x_trends()
        except Exception as e:
            print(f"  [WARN] X 采集失败: {e}")
    else:
        print("  ✗ 跳过（模块未加载）")

    # --- 6. Reddit 热点 ---
    print("[5/7] Reddit 热帖...")
    reddit_hot = []
    if fetch_reddit_hot:
        try:
            reddit_hot = fetch_reddit_hot()
        except Exception as e:
            print(f"  [WARN] Reddit 采集失败: {e}")
    else:
        print("  ✗ 跳过（模块未加载）")

    # --- 7. 读取本地运营日报 ---
    print("[6.5/7] 读取运营日报...")
    daily_report = ""
    daily_paths = [
        Path.home() / ".openclaw" / "workspace" / "byreal-daily" / f"daily-{today}.txt",
        BASE_DIR.parent / "byreal-daily" / f"daily-{today}.txt",
    ]
    for dp in daily_paths:
        if dp.exists():
            daily_report = dp.read_text(encoding="utf-8")
            print(f"  ✓ 读取日报: {dp}")
            break
    if not daily_report:
        print("  ✗ 未找到今日日报")

    # --- 7. AI 总结 ---
    print("[7/7] AI 总结...")
    ai_summary = generate_ai_summary(summary, market, comps, alerts)

    # --- 8. Byreal 账号分析 (mock data) ---
    print("[8/8] Byreal 账号分析 (mock)...")
    byreal_account = {
        "handle": "@byreal_io",
        "followers": 0,  # TODO: 真实 API
        "followersChange7d": 0,
        "tweets7d": 0,
        "avgEngagement": 0,
        "recentTweets": [],  # 最近推文表现
    }

    # --- 9. 合并输出 ---
    final = {
        "date": today,
        "ts": datetime.now(timezone.utc).isoformat(),
        **summary,
        "market": market,
        "competitors": comps,
        "alerts": alerts,
        "aiInsight": ai_summary.get("insight", ""),
        "aiPublic": ai_summary.get("public", ""),
        "dailyReport": daily_report,
        "xTrends": x_trends,
        "redditHot": reddit_hot,
        "byrealAccount": byreal_account,
    }

    with open(today_dir / "summary.json", "w") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    # latest 软链
    latest = DATA_DIR / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(today_dir.resolve())

    print(f"\n✅ 数据已保存: {today_dir}/")
    print(f"📋 {len(alerts)} 条预警:")
    for a in alerts:
        icon = {"red": "🔴", "orange": "🟠", "green": "🟢"}.get(a["lv"], "⚪")
        print(f"   {icon} [{a['cat']}] {a['msg']}")

    return final


if __name__ == "__main__":
    main()
