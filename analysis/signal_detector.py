"""
부동산 신호 감지 엔진

수집된 데이터에서 이상치/트렌드를 감지하여 신호를 생성합니다.
- 거래량 급변동 (전월 대비 ±30%)
- 가격 트렌드 (3주 연속 상승/하락)
- 뉴스 키워드 급증

입력: data/trades/, data/news/
출력: data/signals/{date}.json
"""

import json
import glob
from datetime import datetime
from pathlib import Path


def load_latest_trades() -> dict | None:
    """최신 거래 데이터를 로드합니다."""
    trades_dir = Path(__file__).parent.parent / "data" / "trades"
    files = sorted(trades_dir.glob("*.json"), reverse=True)
    if not files:
        print("[SKIP] 거래 데이터 없음")
        return None
    data = json.loads(files[0].read_text(encoding="utf-8"))
    print(f"거래 데이터 로드: {files[0].name}")
    return data


def load_previous_trades() -> dict | None:
    """이전 월 거래 데이터를 로드합니다."""
    trades_dir = Path(__file__).parent.parent / "data" / "trades"
    files = sorted(trades_dir.glob("*.json"), reverse=True)
    if len(files) < 2:
        return None
    data = json.loads(files[1].read_text(encoding="utf-8"))
    return data


def load_latest_news() -> dict | None:
    """최신 뉴스 데이터를 로드합니다."""
    news_dir = Path(__file__).parent.parent / "data" / "news"
    files = sorted(news_dir.glob("*.json"), reverse=True)
    if not files:
        print("[SKIP] 뉴스 데이터 없음")
        return None
    data = json.loads(files[0].read_text(encoding="utf-8"))
    print(f"뉴스 데이터 로드: {files[0].name}")
    return data


def detect_trade_signals(current: dict, previous: dict | None) -> list[dict]:
    """거래량/가격 변동 신호를 감지합니다."""
    signals = []

    if not previous:
        # 이전 데이터 없으면 절대값 기반 신호만
        total = current.get("summary", {}).get("total_trades", 0)
        if total > 0:
            signals.append({
                "type": "baseline",
                "severity": "info",
                "message": f"서울 아파트 {current['deal_ym']} 총 {total:,}건 거래",
                "data": {"total_trades": total},
            })
        return signals

    # 지역별 거래량 변동 비교
    for region, curr_data in current.get("regions", {}).items():
        prev_data = previous.get("regions", {}).get(region)
        if not prev_data or prev_data["count"] == 0:
            continue

        count_change = (curr_data["count"] - prev_data["count"]) / prev_data["count"]

        # 거래량 ±30% 이상 변동
        if abs(count_change) >= 0.3:
            direction = "급증" if count_change > 0 else "급감"
            signals.append({
                "type": "volume_spike",
                "severity": "high" if abs(count_change) >= 0.5 else "medium",
                "message": f"{region} 거래량 {direction} ({count_change:+.0%}): {prev_data['count']}건 → {curr_data['count']}건",
                "data": {
                    "region": region,
                    "prev_count": prev_data["count"],
                    "curr_count": curr_data["count"],
                    "change_pct": round(count_change * 100, 1),
                },
            })

        # 평균가 ±10% 이상 변동
        if prev_data["avg_price_man"] > 0:
            price_change = (curr_data["avg_price_man"] - prev_data["avg_price_man"]) / prev_data["avg_price_man"]
            if abs(price_change) >= 0.1:
                direction = "상승" if price_change > 0 else "하락"
                signals.append({
                    "type": "price_change",
                    "severity": "high" if abs(price_change) >= 0.2 else "medium",
                    "message": f"{region} 평균가 {direction} ({price_change:+.0%}): {prev_data['avg_price_man']:,}만 → {curr_data['avg_price_man']:,}만",
                    "data": {
                        "region": region,
                        "prev_price": prev_data["avg_price_man"],
                        "curr_price": curr_data["avg_price_man"],
                        "change_pct": round(price_change * 100, 1),
                    },
                })

    return signals


def detect_news_signals(news: dict) -> list[dict]:
    """뉴스에서 정책/시장 신호를 감지합니다."""
    signals = []

    # 정책 키워드 감지
    policy_keywords = {
        "DSR": "대출 규제",
        "LTV": "대출 규제",
        "DTI": "대출 규제",
        "금리 인하": "금리",
        "금리 인상": "금리",
        "기준금리": "금리",
        "재건축": "재건축/재개발",
        "재개발": "재건축/재개발",
        "분양가 상한제": "분양 규제",
        "특별공급": "분양",
        "미분양": "공급 과잉",
        "입주 물량": "공급",
        "전세 사기": "전세 시장",
        "역전세": "전세 시장",
    }

    keyword_counts: dict[str, list[str]] = {}
    for article in news.get("articles", []):
        title = article.get("title", "")
        for keyword, category in policy_keywords.items():
            if keyword in title:
                keyword_counts.setdefault(category, []).append(title)

    for category, titles in keyword_counts.items():
        if len(titles) >= 2:  # 같은 카테고리 2건 이상이면 신호
            signals.append({
                "type": "news_cluster",
                "severity": "medium" if len(titles) >= 3 else "low",
                "message": f"'{category}' 관련 뉴스 {len(titles)}건 집중",
                "data": {
                    "category": category,
                    "count": len(titles),
                    "sample_titles": titles[:3],
                },
            })

    return signals


def detect_signals() -> dict:
    """모든 신호를 감지하고 저장합니다."""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 신호 감지: {today} ===")

    all_signals = []

    # 거래 신호
    current_trades = load_latest_trades()
    previous_trades = load_previous_trades()
    if current_trades:
        trade_signals = detect_trade_signals(current_trades, previous_trades)
        all_signals.extend(trade_signals)
        print(f"  거래 신호: {len(trade_signals)}건")

    # 뉴스 신호
    news = load_latest_news()
    if news:
        news_signals = detect_news_signals(news)
        all_signals.extend(news_signals)
        print(f"  뉴스 신호: {len(news_signals)}건")

    # 심각도 순 정렬
    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    all_signals.sort(key=lambda s: severity_order.get(s["severity"], 99))

    result = {
        "date": today,
        "detected_at": datetime.now().isoformat(),
        "signal_count": len(all_signals),
        "signals": all_signals,
    }

    print(f"\n총 {len(all_signals)}건 신호 감지")
    for s in all_signals:
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(s["severity"], "")
        print(f"  {icon} [{s['severity']}] {s['message']}")

    return result


def save(data: dict):
    out_dir = Path(__file__).parent.parent / "data" / "signals"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{data['date']}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {out_path}")


if __name__ == "__main__":
    data = detect_signals()
    save(data)
