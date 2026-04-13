"""
AI 뉴스레터 초안 생성기

수집된 신호 + 뉴스를 Claude에 전달하여 주간 뉴스레터 초안을 생성합니다.
출력: drafts/{date}.md
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """당신은 한국 부동산 시장을 분석하는 전문 뉴스레터 작성자입니다.
이름: Asset Oracle

규칙:
1. 팩트 기반: 모든 주장에 출처/수치를 명시
2. 선행 지표 중심: "이미 사실인 신호"를 찾고, 그것이 어떤 결과로 이어질지 분석
3. 예측은 구체적으로: "4주 뒤" + "구체적 헤드라인" + "날짜" 형식
4. 틀린 예측은 왜 틀렸는지 공개 해부
5. 톤: 전문적이되 읽기 쉽게. 한국어로 작성."""

NEWSLETTER_PROMPT = """아래 데이터를 분석하여 주간 뉴스레터 초안을 작성해주세요.

## 입력 데이터

### 감지된 신호
{signals}

### 이번 주 뉴스
{news}

### 거래 데이터 요약
{trades}

## 출력 형식 (마크다운)

# 🏠 Asset Oracle — Week {week_num}

## 📡 이번 주 신호 3개
(가장 중요한 선행 지표 3개를 선정. 각각 1-2줄로 설명. 출처/수치 포함)

## 🔮 4주 뒤 예측
(구체적인 헤드라인 1개. 날짜 명시. 근거 2줄)
> **"예측 헤드라인"**
> 예상 시점: YYYY-MM-DD
> 근거: ...

## 💡 이번 주 액션
(독자가 지금 할 수 있는 구체적 행동 1개)

## 📊 데이터 스냅샷
(핵심 수치 3-4개를 표로 정리)
"""


def load_latest_file(subdir: str) -> dict | None:
    data_dir = Path(__file__).parent.parent / "data" / subdir
    files = sorted(data_dir.glob("*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def generate_draft() -> str:
    """AI를 사용하여 뉴스레터 초안을 생성합니다."""
    signals = load_latest_file("signals")
    news = load_latest_file("news")
    trades = load_latest_file("trades")

    # 주차 계산
    week_num = datetime.now().isocalendar()[1]
    target_date = (datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%d")

    signals_text = json.dumps(signals.get("signals", []), ensure_ascii=False, indent=2) if signals else "신호 데이터 없음"
    news_text = "\n".join(
        f"- {a['title']} ({a.get('source', '')})"
        for a in (news.get("articles", []) if news else [])[:15]
    ) or "뉴스 데이터 없음"
    trades_text = json.dumps(trades.get("summary", {}), ensure_ascii=False, indent=2) if trades else "거래 데이터 없음"

    prompt = NEWSLETTER_PROMPT.format(
        signals=signals_text,
        news=news_text,
        trades=trades_text,
        week_num=week_num,
    )

    if not ANTHROPIC_API_KEY:
        print("[SKIP] ANTHROPIC_API_KEY not set - 더미 초안 생성")
        return _dummy_draft(week_num, signals, news, trades)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"[ERROR] Claude API: {e}")
        return _dummy_draft(week_num, signals, news, trades)


def _dummy_draft(week_num: int, signals: dict | None, news: dict | None, trades: dict | None) -> str:
    """API 키 없을 때 더미 초안을 생성합니다."""
    signal_lines = ""
    if signals:
        for i, s in enumerate(signals.get("signals", [])[:3], 1):
            signal_lines += f"{i}. **{s.get('message', 'N/A')}**\n"
    else:
        signal_lines = "1. 데이터 수집 후 업데이트 예정\n"

    news_lines = ""
    if news:
        for a in news.get("articles", [])[:5]:
            news_lines += f"- {a['title']}\n"

    target_date = (datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%d")

    return f"""# 🏠 Asset Oracle — Week {week_num}

## 📡 이번 주 신호 3개
{signal_lines}
## 🔮 4주 뒤 예측
> **"[예측 헤드라인 - 데이터 분석 후 작성]"**
> 예상 시점: {target_date}
> 근거: 수집된 데이터를 기반으로 작성 예정

## ✅ 지난 예측 검증
| 예측일 | 예측 내용 | 결과 | 분석 |
|--------|----------|------|------|
| (첫 발행) | - | - | - |

## 💡 이번 주 액션
- 데이터 파이프라인 가동 시작. 다음 주부터 본격 분석.

## 📊 주요 뉴스
{news_lines}
---
*Asset Oracle은 공개 데이터와 AI 분석을 기반으로 한국 부동산 시장의 선행 지표를 추적합니다.*
*모든 예측은 기록되며, 틀린 예측은 공개적으로 해부합니다.*
"""


def save_draft(content: str):
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(__file__).parent.parent / "drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"초안 저장: {out_path}")


if __name__ == "__main__":
    print("=== 뉴스레터 초안 생성 ===")
    draft = generate_draft()
    save_draft(draft)
    print("\n--- 미리보기 ---")
    preview = draft[:500] + "..." if len(draft) > 500 else draft
    print(preview.encode("utf-8", errors="replace").decode("utf-8"))
