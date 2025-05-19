import os
import redis
from celery import Celery
from transformers import pipeline

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
celery = Celery("analyzer_worker", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

classifier = pipeline(
    "sentiment-analysis",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english"
)

@celery.task(name="analyzer_worker.analyzer_text", queue="analyzer_queue")
def analyzer_text(text):
    print("[STT] → [Analyzer] Celery 전달 text 수신")
    try:
        decoded_text = text
        print(f"[Analyzer] 🎙️ 텍스트 수신: {decoded_text}")
        result = classifier(decoded_text)[0]
    except Exception as e:
        print(f"[Analyzer] Sentiment analysis error: {e}")
        return

    emotion = "긍정" if result["label"] == "POSITIVE" else "부정"
    icon = "👍" if result["label"] == "POSITIVE" else "👎"
    score = result["score"]

    output = f"{icon} {emotion} [{score * 100:.0f}%] : {decoded_text}"
    try:
        r.publish("result_channel", output)
    except Exception as e:
        print(f"[Analyzer] Redis publish error: {e}")
        return
    print(f"[Analyzer] ✅ publish 완료: {output}")
