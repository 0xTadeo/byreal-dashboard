#!/usr/bin/env python3
"""
Reddit 热点采集
使用 Reddit JSON API (无需认证)
"""

import json
import urllib.request
import urllib.error
import time

SUBREDDITS = ["solana", "defi", "cryptocurrency"]
BYREAL_KEYWORDS = ["byreal", "solana", "dex"]


def fetch_reddit_hot():
    """
    采集 Reddit 热帖
    使用 Reddit 公开 JSON API
    """
    print("  采集 Reddit 热帖...")
    
    all_posts = []
    
    for sub in SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=5"
            req = urllib.request.Request(url, headers={
                "User-Agent": "ByealBot/1.0"
            })
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    p = post.get("data", {})
                    
                    # 检查是否与 Byreal/Solana 相关
                    title = p.get("title", "").lower()
                    selftext = p.get("selftext", "").lower()
                    is_relevant = any(kw in title or kw in selftext for kw in BYREAL_KEYWORDS)
                    
                    all_posts.append({
                        "subreddit": sub,
                        "title": p.get("title", ""),
                        "author": p.get("author", ""),
                        "score": p.get("score", 0),
                        "upvoteRatio": p.get("upvote_ratio", 0),
                        "numComments": p.get("num_comments", 0),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "created": p.get("created_utc", 0),
                        "isRelevant": is_relevant,
                        "flair": p.get("link_flair_text", ""),
                    })
            
            # 礼貌等待，避免被限速
            time.sleep(1)
            
        except Exception as e:
            print(f"  [WARN] Reddit r/{sub} 采集失败: {e}")
            continue
    
    # 按 score 排序
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"  ✓ 采集到 {len(all_posts)} 条 Reddit 帖子")
    relevant_count = sum(1 for p in all_posts if p["isRelevant"])
    if relevant_count > 0:
        print(f"  → {relevant_count} 条与 Byreal/Solana 相关")
    
    return all_posts


def main():
    """独立运行入口"""
    posts = fetch_reddit_hot()
    print(json.dumps(posts, indent=2, ensure_ascii=False))
    return posts


if __name__ == "__main__":
    main()
