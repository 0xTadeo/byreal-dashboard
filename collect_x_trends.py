#!/usr/bin/env python3
"""
X/Twitter 热点采集
优先读取本地缓存 (data/x_cache.json)，由 Camofox 定期抓取更新
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
X_CACHE = BASE_DIR / "data" / "x_cache.json"


def fetch_x_trends():
    """从本地缓存读取 X 推文数据"""
    print("  采集 X/Twitter 热点...")

    if X_CACHE.exists():
        try:
            with open(X_CACHE) as f:
                trends = json.load(f)
            real_count = sum(1 for t in trends if t.get("content") and "暂无" not in t["content"])
            print(f"  ✓ 从缓存读取 {len(trends)} 条推文 ({real_count} 条真实)")
            return trends
        except Exception as e:
            print(f"  ✗ 缓存读取失败: {e}")

    print("  ✗ 无缓存数据，返回空列表")
    return []


def main():
    trends = fetch_x_trends()
    print(json.dumps(trends[:3], indent=2, ensure_ascii=False))
    return trends


if __name__ == "__main__":
    main()
