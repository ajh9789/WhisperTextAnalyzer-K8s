# =============================================
# ✅ analyzer_worker/analyzer_worker.py 개선 버전
# =============================================
import os
import redis
from celery import Celery
from transformers import pipeline

# 🎯 DOCKER 환경변수 유무로 판단
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

app = Celery('analyzer_worker', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

classifier = pipeline("sentiment-analysis")

@app.task
def analyze_text():
    print("[Analyzer] polling text_queue...")
    text = r.rpop("text_queue")
    if not text:
        print("[Analyzer] queue empty.")
        return

    result = classifier(text.decode())[0]
    output = f"{text.decode()} → {result['label']} ({result['score']:.2f})"

    r.publish("result_channel", output)
    print(f"✅ Published result: {output}")

if __name__ == "__main__":
    while True:
        analyze_text()
