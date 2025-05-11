# ✅ analyzer_worker/analyzer_worker.py

import os
import redis
from transformers import pipeline

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

classifier = pipeline("sentiment-analysis")

positive_count = 0
positive_score_sum = 0.0
negative_count = 0
negative_score_sum = 0.0

def analyze_text():
    global positive_count, positive_score_sum, negative_count, negative_score_sum

    print("[Analyzer] ⏳ polling text_queue...")
    text = r.rpop("text_queue")
    if not text:
        print("[Analyzer] 💤 queue empty")
        return

    print(f"[Analyzer] 🎙️ text found, analyzing: {text.decode()}")
    result = classifier(text.decode())[0]

    emotion = "긍정" if result['label'] == "POSITIVE" else "부정"
    icon = "✅" if result['label'] == "POSITIVE" else "❌"
    score = result['score']

    if result['label'] == "POSITIVE":
        positive_count += 1
        positive_score_sum += score
    else:
        negative_count += 1
        negative_score_sum += score

    output = f"{icon}{emotion}[{score:.2f}] : {text.decode()}"
    r.publish("result_channel", output)

    print(f"[Analyzer] ✅ published result: {output}")
    print(f"[Analyzer] 통계 → 긍정: {positive_count}회, 평균 {positive_score_sum/positive_count if positive_count else 0:.2f} / 부정: {negative_count}회, 평균 {negative_score_sum/negative_count if negative_count else 0:.2f}")

if __name__ == "__main__":
    print("🚀 Analyzer Worker started.")
    while True:
        analyze_text()