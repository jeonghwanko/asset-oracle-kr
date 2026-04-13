# Asset Oracle KR

한국 부동산 시장의 선행 지표를 AI로 추적하여, 4주 뒤 헤드라인을 예측하는 주간 뉴스레터.

## 구조

```
collectors/     → 데이터 수집 (국토부, 한은, 부동산원, 뉴스)
analysis/       → 신호 감지 + AI 요약/예측
newsletter/     → 뉴스레터 템플릿 + 발행
tracker/        → 예측 기록 + 검증
data/           → 수집된 데이터 (JSON)
drafts/         → 뉴스레터 초안
```

## 시작하기

```bash
cp .env.example .env
# .env에 API 키 입력

pip install -r requirements.txt

# 데이터 수집
python collectors/molit_trades.py
python collectors/news_crawler.py

# 신호 분석
python analysis/signal_detector.py

# 뉴스레터 초안 생성
python analysis/ai_summarizer.py
```

## 주간 발행 프로세스

1. 매일 자동 수집 (GitHub Actions)
2. 금요일: AI 초안 생성
3. 토요일: 검토/수정 후 발행
