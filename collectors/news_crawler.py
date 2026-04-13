"""
네이버 뉴스 부동산 섹션 크롤러 + 정부 보도자료 모니터링

소스: 네이버 뉴스 RSS (부동산), 국토부 보도자료
출력: data/news/{date}.json
"""

import json
import re
from datetime import datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

# 네이버 뉴스 RSS — 부동산 관련 키워드 검색
NAVER_RSS_URLS = [
    "https://news.google.com/rss/search?q=부동산+시장&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=아파트+매매&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=부동산+정책&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=금리+부동산&hl=ko&gl=KR&ceid=KR:ko",
]

# 국토교통부 보도자료 RSS
MOLIT_PRESS_URL = "https://www.molit.go.kr/USR/BORD0201/m_69/RSS.jsp"


def fetch_rss(url: str, max_items: int = 10) -> list[dict]:
    """RSS 피드에서 뉴스 항목을 수집합니다."""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            items.append({
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", ""),
            })
        return items
    except Exception as e:
        print(f"[ERROR] RSS {url[:50]}…: {e}")
        return []


def fetch_molit_press(max_items: int = 10) -> list[dict]:
    """국토교통부 보도자료를 수집합니다."""
    try:
        feed = feedparser.parse(MOLIT_PRESS_URL)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            # 부동산 관련 키워드 필터
            keywords = ["부동산", "주택", "아파트", "전세", "매매", "분양", "임대", "재건축", "재개발", "LTV", "DTI", "DSR", "금리"]
            if any(kw in title for kw in keywords):
                items.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": "국토교통부",
                })
        return items
    except Exception as e:
        print(f"[ERROR] 국토부 보도자료: {e}")
        return []


def deduplicate(articles: list[dict]) -> list[dict]:
    """제목 기준으로 중복 제거합니다."""
    seen = set()
    result = []
    for a in articles:
        # 제목에서 공백/특수문자 제거 후 비교
        key = re.sub(r"\s+", "", a["title"])
        if key not in seen:
            seen.add(key)
            result.append(a)
    return result


def collect_news() -> dict:
    """오늘의 부동산 뉴스를 수집합니다."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 뉴스 수집: {today} ===")

    all_articles = []

    # Google News RSS (부동산 키워드)
    for url in NAVER_RSS_URLS:
        articles = fetch_rss(url, max_items=10)
        all_articles.extend(articles)
        print(f"  RSS: {len(articles)}건")

    # 국토부 보도자료
    press = fetch_molit_press()
    all_articles.extend(press)
    print(f"  국토부 보도자료: {len(press)}건")

    # 중복 제거
    unique = deduplicate(all_articles)
    print(f"\n총 {len(unique)}건 (중복 제거 후)")

    result = {
        "date": today,
        "collected_at": datetime.now().isoformat(),
        "count": len(unique),
        "articles": unique,
    }

    return result


def save(data: dict):
    """수집 결과를 JSON으로 저장합니다."""
    out_dir = Path(__file__).parent.parent / "data" / "news"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{data['date']}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {out_path}")


if __name__ == "__main__":
    data = collect_news()
    save(data)
