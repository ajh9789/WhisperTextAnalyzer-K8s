# =============================================
# ✅ analyzer_worker/analyzer_worker.py (개선판)
# =============================================

import os
import redis
from celery import Celery
from transformers import pipeline

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

celery_app = Celery("analyzer_worker", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

classifier = pipeline(
    "sentiment-analysis",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english"
)

# ✅ 통계 변수 초기화
positive_count = 0
positive_score_sum = 0.0
negative_count = 0
negative_score_sum = 0.0

@celery_app.task
def analyze_text():
    """
    Redis의 text_queue에서 텍스트를 가져와 감정 분석 후 result_channel로 publish
    """
    global positive_count, positive_score_sum, negative_count, negative_score_sum

    print("[Analyzer] ⏳ polling text_queue...")
    try:
        text = r.rpop("text_queue")
    except Exception as e:
        print(f"[Analyzer] Redis error: {e}")
        return

    if not text:
        print("[Analyzer] 💤 queue empty")
        return

    try:
        print(f"[Analyzer] 🎙️ text found, analyzing: {text.decode()}")
        result = classifier(text.decode())[0]
    except Exception as e:
        print(f"[Analyzer] Sentiment analysis error: {e}")
        return

    emotion = "긍정" if result["label"] == "POSITIVE" else "부정"
    icon = "✅" if result["label"] == "POSITIVE" else "❌"
    score = result["score"]

    if result["label"] == "POSITIVE":
        positive_count += 1
        positive_score_sum += score
    else:
        negative_count += 1
        negative_score_sum += score

    output = f"{icon} {emotion} [{score:.2f}] : {text.decode()}"
    try:
        r.publish("result_channel", output)
    except Exception as e:
        print(f"[Analyzer] Redis publish error: {e}")
        return

    print(f"[Analyzer] ✅ published result: {output}")
    print(
        f"[Analyzer] 통계 → 긍정: {positive_count}회, 평균 {positive_score_sum/positive_count if positive_count else 0:.2f} / "
        f"부정: {negative_count}회, 평균 {negative_score_sum/negative_count if negative_count else 0:.2f}"
    )