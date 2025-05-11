# ✅ analyzer_worker.py 개선 버전 (Polling 방식)
import os
import redis
import sqlite3
from transformers import pipeline
import time

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 0.5))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
classifier = pipeline("sentiment-analysis")
print("✅ Sentiment classifier 로드 완료")

def analyze_text():
    try:
        text_bytes = r.rpop("text_queue")
        if not text_bytes:
            return

        text = text_bytes.decode("utf-8")
        result = classifier(text)[0]
        emotion = result['label']

        with sqlite3.connect("results.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS results (text TEXT, emotion TEXT)")
            conn.execute("INSERT INTO results VALUES (?, ?)", (text, emotion))
            conn.commit()

        r.publish("result_channel", f"{text} → {emotion}")
        print(f"✅ 분석 결과 → {text} → {emotion}")

    except Exception as e:
        print(f"❌ analyzer 오류: {e}")

if __name__ == "__main__":
    print("📢 Analyzer polling 시작")
    while True:
        analyze_text()
        time.sleep(POLL_INTERVAL)
