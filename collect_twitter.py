#!/usr/bin/env python3
"""
Byreal Dashboard — Twitter 数据采集
采集方式:
  1. 浏览器自动化 (Playwright) — 精确抓取粉丝数、互动数
  2. Web Search 备选 — 通过搜索引擎获取公开信息

用法: python3 collect_twitter.py
依赖: pip install playwright && playwright install chromium
"""

import json
import os
import sys
import time
import re
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# ============================================================
# 追踪账号配置
# ============================================================
ACCOUNTS = {
    # 官方
    "Byreal_io": {"type": "official", "label": "Byreal 官方"},
    # 竞品
    "JupiterExchange": {"type": "competitor", "label": "Jupiter"},
    "RaydiumProtocol": {"type": "competitor", "label": "Raydium"},
    "MeteoraAG": {"type": "competitor", "label": "Meteora"},
    "aborrowofficial": {"type": "competitor", "label": "Orca"},
    # KOL (可随时增减)
    # "KOL_handle": {"type": "kol", "label": "KOL名称"},
}


# ============================================================
# 方法1: Playwright 浏览器自动化
# ============================================================
def collect_playwright():
    """使用 Playwright 抓取 Twitter/X 页面数据"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  Playwright 未安装，跳过浏览器自动化")
        print("  安装: pip install playwright && playwright install chromium")
        return None

    results = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 800},
            )

            for handle, info in ACCOUNTS.items():
                print(f"  抓取 @{handle}...")
                page = ctx.new_page()
                try:
                    page.goto(f"https://x.com/{handle}", timeout=20000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)

                    # 获取页面文本，解析粉丝数
                    text = page.content()

                    # 尝试多种方式解析 followers
                    followers = None

                    # 方法A: 从 aria-label 或 title 获取
                    try:
                        el = page.locator(f'a[href="/{handle}/verified_followers"]').first
                        if el:
                            txt = el.inner_text()
                            followers = parse_count(txt)
                    except:
                        pass

                    # 方法B: 从页面文本搜索
                    if not followers:
                        m = re.search(r'([\d,.]+[KkMm]?)\s*(?:Followers|followers)', text)
                        if m:
                            followers = parse_count(m.group(1))

                    # 获取最近推文互动（可选）
                    results[handle] = {
                        "label": info["label"],
                        "type": info["type"],
                        "followers": followers,
                        "source": "playwright",
                    }
                except Exception as e:
                    print(f"    ✗ @{handle} 抓取失败: {e}")
                    results[handle] = {
                        "label": info["label"],
                        "type": info["type"],
                        "followers": None,
                        "source": "playwright",
                        "error": str(e),
                    }
                finally:
                    page.close()
                time.sleep(2)  # 防止限速

            browser.close()
    except Exception as e:
        print(f"  Playwright 运行错误: {e}")
        return None

    return results


# ============================================================
# 方法2: SocialBlade / 公开 API 备选
# ============================================================
def collect_socialblade_fallback():
    """通过公开信息源获取粗略数据"""
    results = {}
    for handle, info in ACCOUNTS.items():
        print(f"  查询 @{handle}...")
        try:
            # 尝试 Nitter 实例（去中心化 Twitter 前端）
            nitter_instances = [
                f"https://nitter.privacydev.net/{handle}",
            ]
            for url in nitter_instances:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        html = resp.read().decode("utf-8")
                        # Nitter 页面中粉丝数格式
                        m = re.search(r'class="profile-stat-num"[^>]*>([\d,]+)', html)
                        if m:
                            results[handle] = {
                                "label": info["label"],
                                "type": info["type"],
                                "followers": int(m.group(1).replace(",", "")),
                                "source": "nitter",
                            }
                            break
                except:
                    continue

            if handle not in results:
                results[handle] = {
                    "label": info["label"],
                    "type": info["type"],
                    "followers": None,
                    "source": "fallback",
                    "error": "公开源不可用",
                }
        except Exception as e:
            results[handle] = {
                "label": info["label"],
                "type": info["type"],
                "followers": None,
                "source": "fallback",
                "error": str(e),
            }
        time.sleep(1)

    return results


# ============================================================
# 工具函数
# ============================================================
def parse_count(text):
    """解析 '12.5K', '1.2M', '45,678' 等格式"""
    if not text:
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    m = re.match(r'([\d.]+)([KkMm]?)', text)
    if not m:
        return None
    num = float(m.group(1))
    suffix = m.group(2).upper()
    if suffix == "K":
        return int(num * 1000)
    if suffix == "M":
        return int(num * 1000000)
    return int(num)


def load_history(date_str):
    """加载历史 Twitter 数据"""
    from datetime import timedelta
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for days_back in range(1, 8):
        prev = (dt - timedelta(days=days_back)).strftime("%Y-%m-%d")
        f = DATA_DIR / prev / "twitter.json"
        if f.exists():
            with open(f) as fh:
                return json.load(fh)
    return None


# ============================================================
# Main
# ============================================================
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = DATA_DIR / today
    today_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*40}")
    print(f"  Twitter 数据采集 — {today}")
    print(f"{'='*40}\n")

    # 尝试 Playwright，失败则用备选
    print("[1] 尝试 Playwright 浏览器自动化...")
    results = collect_playwright()

    if not results:
        print("\n[2] Playwright 不可用，使用备选方案...")
        results = collect_socialblade_fallback()

    # 计算增长
    history = load_history(today)
    for handle, data in results.items():
        if data.get("followers") and history and handle in history:
            prev = history[handle].get("followers")
            if prev:
                data["followerGrowth"] = data["followers"] - prev
                data["followerGrowthPct"] = (data["followers"] - prev) / prev

    # 保存
    output = {
        "date": today,
        "ts": datetime.now().isoformat(),
        "accounts": results,
    }

    with open(today_dir / "twitter.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 数据已保存: {today_dir}/twitter.json")
    print(f"\n{'='*40}")
    for handle, data in results.items():
        f_str = f"{data['followers']:,}" if data.get("followers") else "N/A"
        growth = ""
        if data.get("followerGrowth"):
            growth = f" ({data['followerGrowth']:+,})"
        print(f"  @{handle} ({data['label']}): {f_str} followers{growth}")

    return output


if __name__ == "__main__":
    main()
