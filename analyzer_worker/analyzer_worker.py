import os
import redis
from celery import Celery
from transformers import pipeline

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

app = Celery('analyzer_worker', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

classifier = pipeline("sentiment-analysis")

@app.task
def analyze_text():
    print("[Analyzer] ⏳ polling text_queue...")
    text = r.rpop("text_queue")
    if not text:
        print("[Analyzer] 💤 queue empty, sleeping.")
        return

    print(f"[Analyzer] 🎙️ text found, analyzing: {text.decode()}")
    result = classifier(text.decode())[0]
    output = f"{text.decode()} → {result['label']} ({result['score']:.2f})"

    r.publish("result_channel", output)
    print(f"[Analyzer] ✅ published result: {output}")

if __name__ == "__main__":
    print("🚀 Analyzer Worker started.")
    while True:
        analyze_text()
