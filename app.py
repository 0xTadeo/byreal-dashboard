#!/usr/bin/env python3
"""
Byreal Ops Dashboard — Streamlit 版
"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置
# ============================================================
st.set_page_config(
    page_title="Byreal Ops Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path(__file__).parent / "data"


# ============================================================
# 样式
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');
    
    .stApp { background-color: #0a0e17; }
    .block-container { padding-top: 2rem; max-width: 1400px; }
    
    h1, h2, h3, h4, h5, h6, p, span, div, li { color: #f1f5f9 !important; }
    
    .metric-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #22d3ee !important;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8 !important;
        margin-top: 0.3rem;
    }
    .metric-change-up { color: #10b981 !important; font-size: 0.85rem; }
    .metric-change-down { color: #ef4444 !important; font-size: 0.85rem; }
    
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #22d3ee !important;
        margin: 1.5rem 0 0.8rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1e293b;
    }
    
    .alert-red { background: #ef444420; border-left: 3px solid #ef4444; padding: 0.6rem 1rem; border-radius: 6px; margin: 0.3rem 0; }
    .alert-orange { background: #f59e0b20; border-left: 3px solid #f59e0b; padding: 0.6rem 1rem; border-radius: 6px; margin: 0.3rem 0; }
    .alert-green { background: #10b98120; border-left: 3px solid #10b981; padding: 0.6rem 1rem; border-radius: 6px; margin: 0.3rem 0; }
    
    .pool-table { width: 100%; }
    .pool-table th { 
        background: #151d2e; 
        color: #94a3b8 !important; 
        padding: 0.6rem 0.8rem; 
        font-size: 0.8rem; 
        text-align: right;
        border-bottom: 1px solid #1e293b;
    }
    .pool-table th:first-child { text-align: left; }
    .pool-table td { 
        padding: 0.6rem 0.8rem; 
        font-family: 'JetBrains Mono', monospace; 
        font-size: 0.85rem;
        text-align: right;
        border-bottom: 1px solid #1e293b10;
    }
    .pool-table td:first-child { 
        text-align: left; 
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
    }
    .pool-table tr:hover { background: #1c2840; }
    
    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    
    div[data-testid="stMetric"] { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 1rem; }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #22d3ee !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 数据加载
# ============================================================
@st.cache_data(ttl=300)
def load_data():
    summary_path = DATA_DIR / "latest" / "summary.json"
    if not summary_path.exists():
        return None
    with open(summary_path) as f:
        return json.load(f)


def fmt_usd(val):
    if val >= 1_000_000_000:
        return f"${val/1e9:.2f}B"
    if val >= 1_000_000:
        return f"${val/1e6:.2f}M"
    if val >= 1_000:
        return f"${val/1e3:.1f}K"
    return f"${val:.0f}"


def fmt_pct(val):
    if val is None:
        return "—"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {abs(val)*100:.1f}%"


# ============================================================
# 主页面
# ============================================================
data = load_data()

if not data:
    st.error("❌ 未找到数据，请先运行 `python3 collect.py`")
    st.stop()

p = data["platform"]
m = data["market"]
alerts = data.get("alerts", [])

# Header
st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1.5rem;">
    <div>
        <h1 style="font-size:1.8rem; font-weight:700; margin:0;">⚡ Byreal Ops Dashboard</h1>
        <p style="color:#64748b !important; font-size:0.9rem; margin:0.3rem 0 0 0;">{data['date']} · 更新于 {data.get('ts', '')[:19].replace('T', ' ')} UTC</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ━━━━ 预警 ━━━━
red_alerts = [a for a in alerts if a["lv"] == "red"]
orange_alerts = [a for a in alerts if a["lv"] == "orange"]
green_alerts = [a for a in alerts if a["lv"] == "green"]

if red_alerts or orange_alerts:
    st.markdown('<div class="section-title">⚠️ 行动项</div>', unsafe_allow_html=True)
    for a in red_alerts:
        st.markdown(f'<div class="alert-red">🔴 {a["msg"]}</div>', unsafe_allow_html=True)
    for a in orange_alerts:
        st.markdown(f'<div class="alert-orange">🟠 {a["msg"]}</div>', unsafe_allow_html=True)
    for a in green_alerts:
        st.markdown(f'<div class="alert-green">🟢 {a["msg"]}</div>', unsafe_allow_html=True)

# ━━━━ 平台概览 ━━━━
st.markdown('<div class="section-title">📊 平台概览</div>', unsafe_allow_html=True)

cols = st.columns(6)
metrics = [
    ("TVL", fmt_usd(p["tvl"]), fmt_pct(p.get("tvlChange")) if p.get("tvlChange") is not None else None),
    ("24h 交易量", fmt_usd(p["vol24h"]), fmt_pct(p.get("volChange")) if p.get("volChange") is not None else None),
    ("7d 交易量", fmt_usd(p["vol7d"]), None),
    ("24h 手续费", fmt_usd(p["fee24h"]), None),
    ("24h 协议收入", fmt_usd(p["rev24h"]), None),
    ("活跃池", f"{p['active']}/{p['total']}", None),
]

for col, (label, value, change) in zip(cols, metrics):
    with col:
        change_html = ""
        if change:
            cls = "metric-change-up" if "▲" in change else "metric-change-down"
            change_html = f'<div class="{cls}">{change}</div>'
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {change_html}
        </div>
        """, unsafe_allow_html=True)

# ━━━━ 市场环境 ━━━━
st.markdown('<div class="section-title">🌍 市场环境</div>', unsafe_allow_html=True)

mcols = st.columns(4)
sol = m.get("sol", {})
btc = m.get("btc", {})
eth = m.get("eth", {})
fng = m.get("fearGreed", {})

market_items = [
    ("SOL", f"${sol.get('price', 0):.2f}", sol.get("change24h", 0)),
    ("BTC", f"${btc.get('price', 0):,.0f}", btc.get("change24h", 0)),
    ("ETH", f"${eth.get('price', 0):,.0f}", eth.get("change24h", 0)),
    ("Fear & Greed", str(fng.get("value", "?")), None),
]

for col, (label, value, change) in zip(mcols, market_items):
    with col:
        change_html = ""
        if change is not None:
            color = "#10b981" if change >= 0 else "#ef4444"
            arrow = "▲" if change >= 0 else "▼"
            change_html = f'<div style="color:{color} !important; font-size:0.85rem;">{arrow} {abs(change):.1f}%</div>'
        elif label == "Fear & Greed":
            fg_val = fng.get("value", 50)
            color = "#ef4444" if fg_val < 25 else "#f59e0b" if fg_val < 50 else "#10b981" if fg_val < 75 else "#22d3ee"
            change_html = f'<div style="color:{color} !important; font-size:0.85rem;">{fng.get("label", "")}</div>'
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {change_html}
        </div>
        """, unsafe_allow_html=True)

# ━━━━ 业务线 ━━━━
st.markdown('<div class="section-title">📦 业务线分布</div>', unsafe_allow_html=True)

biz = data.get("bizLines", {})
biz_rows = []
for key in ["xStocks", "Gold_RWA", "Major", "Stablecoin", "Other"]:
    b = biz.get(key)
    if b and b["tvl"] > 0:
        share = b["tvl"] / p["tvl"] * 100 if p["tvl"] > 0 else 0
        biz_rows.append({
            "业务线": key,
            "TVL": fmt_usd(b["tvl"]),
            "占比": f"{share:.1f}%",
            "24h Vol": fmt_usd(b["vol24h"]),
            "24h Fee": fmt_usd(b["fee24h"]),
            "池数": b["count"],
        })

if biz_rows:
    biz_html = '<table class="pool-table"><tr>'
    for h in biz_rows[0].keys():
        biz_html += f'<th>{h}</th>'
    biz_html += '</tr>'
    for row in biz_rows:
        biz_html += '<tr>'
        for v in row.values():
            biz_html += f'<td>{v}</td>'
        biz_html += '</tr>'
    biz_html += '</table>'
    st.markdown(biz_html, unsafe_allow_html=True)

# ━━━━ 竞品对比 ━━━━
st.markdown('<div class="section-title">🏆 竞品对比</div>', unsafe_allow_html=True)

comps = data.get("competitors", {})
comp_rows = []
for slug, c in sorted(comps.items(), key=lambda x: x[1].get("tvl", 0), reverse=True):
    marker = " ⭐" if slug == "byreal" else ""
    comp_rows.append({
        "协议": c.get("name", slug) + marker,
        "TVL": fmt_usd(c.get("tvl", 0)),
        "24h Vol": fmt_usd(c.get("vol24h", 0)) if c.get("vol24h") else "—",
        "7d Vol": fmt_usd(c.get("vol7d", 0)) if c.get("vol7d") else "—",
    })

if comp_rows:
    comp_html = '<table class="pool-table"><tr>'
    for h in comp_rows[0].keys():
        comp_html += f'<th>{h}</th>'
    comp_html += '</tr>'
    for row in comp_rows:
        comp_html += '<tr>'
        for v in row.values():
            comp_html += f'<td>{v}</td>'
        comp_html += '</tr>'
    comp_html += '</table>'
    st.markdown(comp_html, unsafe_allow_html=True)

# ━━━━ xStocks ━━━━
xs = data.get("xStocks", [])
if xs:
    st.markdown('<div class="section-title">📈 xStocks</div>', unsafe_allow_html=True)
    xs_rows = []
    for s in xs[:12]:
        chg = s.get("pc1d", 0)
        chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg)*100:.1f}%" if chg else "—"
        xs_rows.append({
            "交易对": s["name"],
            "价格": f"${s['px']:.2f}" if s["px"] < 1000 else f"${s['px']:,.0f}",
            "24h 变化": chg_str,
            "TVL": fmt_usd(s["tvl"]),
            "24h Vol": fmt_usd(s["v24h"]),
            "APR": f"{s['apr']*100:.1f}%" if s.get("apr") else "—",
        })
    
    xs_html = '<table class="pool-table"><tr>'
    for h in xs_rows[0].keys():
        xs_html += f'<th>{h}</th>'
    xs_html += '</tr>'
    for row in xs_rows:
        xs_html += '<tr>'
        for i, v in enumerate(row.values()):
            style = ""
            if i == 2 and "▲" in str(v):
                style = ' style="color:#10b981 !important;"'
            elif i == 2 and "▼" in str(v):
                style = ' style="color:#ef4444 !important;"'
            xs_html += f'<td{style}>{v}</td>'
        xs_html += '</tr>'
    xs_html += '</table>'
    st.markdown(xs_html, unsafe_allow_html=True)

# ━━━━ Top 池子 ━━━━
st.markdown('<div class="section-title">🏊 Top 15 池子 (by TVL)</div>', unsafe_allow_html=True)

rankings = data.get("rankings", {})
top_tvl = rankings.get("topTvl", [])
if top_tvl:
    pool_rows = []
    for i, pool in enumerate(top_tvl, 1):
        pool_rows.append({
            "#": i,
            "交易对": pool["name"],
            "业务线": pool["biz"],
            "TVL": fmt_usd(pool["tvl"]),
            "24h Vol": fmt_usd(pool["v24h"]),
            "24h Fee": fmt_usd(pool["f24h"]),
            "APR": f"{pool['apr']*100:.1f}%" if pool.get("apr") else "—",
            "Fee/TVL": f"{pool['ftv']*100:.2f}%" if pool.get("ftv") else "—",
        })
    
    pool_html = '<table class="pool-table"><tr>'
    for h in pool_rows[0].keys():
        pool_html += f'<th>{h}</th>'
    pool_html += '</tr>'
    for row in pool_rows:
        pool_html += '<tr>'
        for v in row.values():
            pool_html += f'<td>{v}</td>'
        pool_html += '</tr>'
    pool_html += '</table>'
    st.markdown(pool_html, unsafe_allow_html=True)

# ━━━━ Top Vol ━━━━
st.markdown('<div class="section-title">🔥 Top 15 池子 (by 24h Volume)</div>', unsafe_allow_html=True)

top_vol = rankings.get("topVol", [])
if top_vol:
    vol_rows = []
    for i, pool in enumerate(top_vol, 1):
        vol_rows.append({
            "#": i,
            "交易对": pool["name"],
            "业务线": pool["biz"],
            "24h Vol": fmt_usd(pool["v24h"]),
            "TVL": fmt_usd(pool["tvl"]),
            "24h Fee": fmt_usd(pool["f24h"]),
        })
    
    vol_html = '<table class="pool-table"><tr>'
    for h in vol_rows[0].keys():
        vol_html += f'<th>{h}</th>'
    vol_html += '</tr>'
    for row in vol_rows:
        vol_html += '<tr>'
        for v in row.values():
            vol_html += f'<td>{v}</td>'
        vol_html += '</tr>'
    vol_html += '</table>'
    st.markdown(vol_html, unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align:center; color:#64748b !important; margin-top:3rem; padding:1rem; border-top:1px solid #1e293b; font-size:0.8rem;">
    Byreal Ops Dashboard · Data refreshed daily at 09:00 UTC+8
</div>
""", unsafe_allow_html=True)
