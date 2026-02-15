#!/usr/bin/env python3
"""
X/Twitter 热点采集
因为 X API 需要付费，先用 mock data + Nitter/jina.ai fallback
"""

import json
import time
from datetime import datetime, timezone

# 关注账号列表
TWITTER_ACCOUNTS = [
    {"handle": "byreal_io", "name": "Byreal", "type": "byreal"},
    {"handle": "JupiterExchange", "name": "Jupiter", "type": "competitor"},
    {"handle": "MeteoraAG", "name": "Meteora", "type": "competitor"},
    {"handle": "Raydium", "name": "Raydium", "type": "competitor"},
    {"handle": "orca_so", "name": "Orca", "type": "competitor"},
    {"handle": "solana", "name": "Solana", "type": "ecosystem"},
    {"handle": "CryptoHayes", "name": "Arthur Hayes", "type": "kol"},
    {"handle": "toly", "name": "Anatoly Yakovenko", "type": "kol"},
]


def fetch_x_trends():
    """
    采集 X/Twitter 热点
    TODO: 当 X API 可用时，替换为真实调用
    现在使用 mock data
    """
    print("  采集 X/Twitter 热点 (mock data)...")
    
    # Mock data - 模拟真实推文结构
    now = datetime.now(timezone.utc)
    trends = []
    
    for acc in TWITTER_ACCOUNTS:
        # 每个账号生成 1-2 条模拟推文
        num_tweets = 1 if acc["type"] == "byreal" else 1
        for i in range(num_tweets):
            tweet = {
                "handle": acc["handle"],
                "name": acc["name"],
                "type": acc["type"],
                "content": f"Mock tweet from @{acc['handle']} - Real data coming soon with X API",
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "timestamp": now.isoformat(),
                "url": f"https://twitter.com/{acc['handle']}/status/mock",
            }
            trends.append(tweet)
    
    # 按时间排序（最新在前）
    trends.sort(key=lambda x: x["timestamp"], reverse=True)
    
    print(f"  ✓ 采集到 {len(trends)} 条推文 (mock)")
    return trends


def main():
    """独立运行入口"""
    trends = fetch_x_trends()
    print(json.dumps(trends, indent=2, ensure_ascii=False))
    return trends


if __name__ == "__main__":
    main()
