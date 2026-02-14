#!/usr/bin/env python3
"""
Byreal Dashboard — Lark 每日推送
用法: python3 push_lark.py [--webhook URL]
默认读取 data/latest/summary.json 推送到 Lark
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent
SUMMARY_PATH = BASE_DIR / "data" / "latest" / "summary.json"

# 从环境变量或命令行获取 webhook
LARK_WEBHOOK = os.environ.get("LARK_WEBHOOK", "")


def fmt(val, prefix="$"):
    if val >= 1_000_000_000:
        return f"{prefix}{val/1e9:.2f}B"
    if val >= 1_000_000:
        return f"{prefix}{val/1e6:.2f}M"
    if val >= 1_000:
        return f"{prefix}{val/1e3:.1f}K"
    return f"{prefix}{val:.0f}"


def pct(val):
    if val is None:
        return "—"
    return f"{'▲' if val >= 0 else '▼'} {abs(val)*100:.1f}%"


def build_message(data):
    p = data["platform"]
    m = data["market"]
    alerts = data.get("alerts", [])

    # 行情
    sol = m.get("sol", {})
    btc = m.get("btc", {})
    eth = m.get("eth", {})
    fng = m.get("fearGreed", {})

    tvl_chg = pct(p.get("tvlChange")) if p.get("tvlChange") is not None else ""
    vol_chg = pct(p.get("volChange")) if p.get("volChange") is not None else ""

    lines = [
        f"📊 Byreal Dashboard — {data['date']}",
        "",
        "━━━━ 平台概览 ━━━━",
        f"TVL: {fmt(p['tvl'])}  {tvl_chg}".strip(),
        f"24h 交易量: {fmt(p['vol24h'])}  {vol_chg}".strip(),
        f"24h 手续费: {fmt(p['fee24h'])}",
        f"24h 协议收入: {fmt(p['rev24h'])}",
        f"活跃池/总池: {p['active']}/{p['total']}",
    ]

    # 业务线
    biz = data.get("bizLines", {})
    if biz:
        lines += ["", "━━━━ 业务分布 ━━━━"]
        for key in ["xStocks", "Gold_RWA", "Major", "Other", "Stablecoin"]:
            b = biz.get(key)
            if b and b["tvl"] > 0:
                share = b["tvl"] / p["tvl"] * 100 if p["tvl"] > 0 else 0
                lines.append(f"  {key}: TVL {fmt(b['tvl'])} ({share:.1f}%) | Vol {fmt(b['vol24h'])} | {b['count']}池")

    # xStocks
    xs = data.get("xStocks", [])
    if xs:
        lines += ["", "━━━━ xStocks ━━━━"]
        for s in xs[:8]:
            chg_str = f"{'▲' if s['pc1d']>=0 else '▼'}{abs(s['pc1d'])*100:.1f}%" if s.get("pc1d") else ""
            lines.append(f"  {s['name']}: TVL {fmt(s['tvl'])} | Vol {fmt(s['v24h'])} | ${s['px']:.2f} {chg_str}")

    # 竞品
    comps = data.get("competitors", {})
    if comps:
        lines += ["", "━━━━ 竞品对比 ━━━━"]
        sorted_c = sorted(comps.items(), key=lambda x: x[1].get("tvl", 0), reverse=True)
        for slug, c in sorted_c:
            marker = " ⭐" if slug == "byreal" else ""
            tvl_str = fmt(c.get("tvl", 0))
            vol_str = fmt(c.get("vol24h", 0)) if c.get("vol24h") else "—"
            lines.append(f"  {c.get('name', slug)}: TVL {tvl_str} | Vol24h {vol_str}{marker}")

    # 预警
    if alerts:
        lines += ["", "━━━━ ⚠️ 行动项 ━━━━"]
        for a in alerts:
            icon = {"red": "🔴", "orange": "🟠", "green": "🟢"}.get(a["lv"], "⚪")
            lines.append(f"  {icon} {a['msg']}")

    # 行情
    lines += [
        "",
        "━━━━ 市场环境 ━━━━",
        f"SOL: ${sol.get('price', 0):.2f} ({sol.get('change24h', 0):+.1f}%)",
        f"BTC: ${btc.get('price', 0):,.0f} ({btc.get('change24h', 0):+.1f}%)",
        f"ETH: ${eth.get('price', 0):,.0f} ({eth.get('change24h', 0):+.1f}%)",
        f"Fear & Greed: {fng.get('value', '?')} ({fng.get('label', '')})",
    ]

    return "\n".join(lines)


def send_lark(webhook, text):
    payload = json.dumps({
        "msg_type": "text",
        "content": {"text": text}
    }).encode("utf-8")

    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result


def main():
    webhook = LARK_WEBHOOK
    for i, arg in enumerate(sys.argv):
        if arg == "--webhook" and i + 1 < len(sys.argv):
            webhook = sys.argv[i + 1]

    if not webhook:
        print("❌ 请设置 LARK_WEBHOOK 环境变量或使用 --webhook 参数")
        print("   export LARK_WEBHOOK='https://open.larksuite.com/open-apis/bot/v2/hook/xxx'")
        sys.exit(1)

    if not SUMMARY_PATH.exists():
        print(f"❌ 未找到数据: {SUMMARY_PATH}")
        print("   请先运行 python3 collect.py")
        sys.exit(1)

    with open(SUMMARY_PATH) as f:
        data = json.load(f)

    text = build_message(data)
    print(text)
    print(f"\n{'='*40}")

    result = send_lark(webhook, text)
    if result.get("code") == 0 or result.get("StatusCode") == 0:
        print("✅ Lark 推送成功")
    else:
        print(f"❌ Lark 推送失败: {result}")


if __name__ == "__main__":
    main()
