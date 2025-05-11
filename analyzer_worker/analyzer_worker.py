# analyzer_worker/analyzer_worker.py → celery worker 사용 X → while loop 실행용으로만 변경

import os
import redis
from transformers import pipeline

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

classifier = pipeline("sentiment-analysis")

def analyze_text():
    print("[Analyzer] ⏳ polling text_queue...")
    text = r.rpop("text_queue")
    if not text:
        print("[Analyzer] 💤 queue empty")
        return

    print(f"[Analyzer] 🎙️ text found, analyzing: {text.decode()}")
    result = classifier(text.decode())[0]
    emotion = "👍긍정" if result['label'] == "POSITIVE" else "👎부정"
    output = f"{emotion}[{result['score']:.2f}]:{text.decode()} "

    r.publish("result_channel", output)
    print(f"[Analyzer] ✅ published result: {output}")

if __name__ == "__main__":
    print("🚀 Analyzer Worker started.")
    while True:
        analyze_text()
