"""
국토교통부 실거래가 공개시스템 — 아파트 매매 실거래가 수집

API: data.go.kr → 국토교통부_아파트매매 실거래자료
필요: MOLIT_API_KEY (.env)
출력: data/trades/{date}.json
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MOLIT_API_KEY", "")
BASE_URL = "http://openapi.molit.go.kr/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

# 주요 지역 코드 (법정동 코드 앞 5자리)
REGIONS = {
    "11110": "서울 종로구",
    "11140": "서울 중구",
    "11170": "서울 용산구",
    "11200": "서울 성동구",
    "11215": "서울 광진구",
    "11230": "서울 동대문구",
    "11260": "서울 중랑구",
    "11290": "서울 성북구",
    "11305": "서울 강북구",
    "11320": "서울 도봉구",
    "11350": "서울 노원구",
    "11380": "서울 은평구",
    "11410": "서울 서대문구",
    "11440": "서울 마포구",
    "11470": "서울 양천구",
    "11500": "서울 강서구",
    "11530": "서울 구로구",
    "11545": "서울 금천구",
    "11560": "서울 영등포구",
    "11590": "서울 동작구",
    "11620": "서울 관악구",
    "11650": "서울 서초구",
    "11680": "서울 강남구",
    "11710": "서울 송파구",
    "11740": "서울 강동구",
}


def fetch_trades(region_code: str, deal_ym: str) -> list[dict]:
    """특정 지역의 특정 월 아파트 매매 실거래가를 조회합니다."""
    if not API_KEY:
        print("[SKIP] MOLIT_API_KEY not set")
        return []

    params = {
        "serviceKey": API_KEY,
        "LAWD_CD": region_code,
        "DEAL_YMD": deal_ym,
        "pageNo": "1",
        "numOfRows": "1000",
        "type": "json",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]
        return items
    except Exception as e:
        print(f"[ERROR] {region_code} {deal_ym}: {e}")
        return []


def collect_monthly(deal_ym: str | None = None) -> dict:
    """주요 지역의 월간 거래 데이터를 수집하고 요약합니다."""
    if deal_ym is None:
        # 전월 데이터 (실거래가는 1~2개월 지연)
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        deal_ym = last_month.strftime("%Y%m")

    print(f"=== 실거래가 수집: {deal_ym} ===")

    result = {
        "deal_ym": deal_ym,
        "collected_at": datetime.now().isoformat(),
        "regions": {},
        "summary": {},
    }

    total_trades = 0
    total_amount = 0

    for code, name in REGIONS.items():
        items = fetch_trades(code, deal_ym)
        count = len(items)

        # 평균 거래가 계산 (만원 단위)
        prices = []
        for item in items:
            price_str = str(item.get("거래금액", item.get("dealAmount", "0")))
            price = int(price_str.replace(",", "").strip())
            if price > 0:
                prices.append(price)

        avg_price = round(sum(prices) / len(prices)) if prices else 0

        result["regions"][name] = {
            "code": code,
            "count": count,
            "avg_price_man": avg_price,
            "max_price_man": max(prices) if prices else 0,
            "min_price_man": min(prices) if prices else 0,
        }

        total_trades += count
        total_amount += sum(prices)

        if count > 0:
            print(f"  {name}: {count}건, 평균 {avg_price:,}만원")

    result["summary"] = {
        "total_trades": total_trades,
        "avg_price_man": round(total_amount / total_trades) if total_trades > 0 else 0,
    }

    print(f"\n총 {total_trades}건 수집완료")
    return result


def save(data: dict):
    """수집 결과를 JSON으로 저장합니다."""
    out_dir = Path(__file__).parent.parent / "data" / "trades"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{data['deal_ym']}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {out_path}")


if __name__ == "__main__":
    data = collect_monthly()
    save(data)
