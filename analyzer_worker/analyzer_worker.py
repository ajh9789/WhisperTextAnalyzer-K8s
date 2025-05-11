# =============================================
# ✅ analyzer_worker/analyzer_worker.py (celery로 개선)
# =============================================

import os
import redis
from transformers import pipeline
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
celery = Celery('analyzer', broker=BROKER_URL)
r = redis.Redis.from_url(BROKER_URL)

classifier = pipeline("sentiment-analysis", model="monologg/koelectra-small-discriminator")

@celery.task(name="analyzer.analyze_text")
def analyze_text():
    text_bytes = r.rpop("text_queue")
    if not text_bytes:
        return

    text = text_bytes.decode("utf-8")
    result = classifier(text)[0]
    emotion = result['label']
    r.publish("result_channel", f"{text} → {emotion}")
