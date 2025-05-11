# ✅ analyzer_worker.py : redis text_queue → transformers 감정분석 → redis result_channel publish

import os
from celery import Celery
import redis
import sqlite3
from transformers import pipeline

# =============================
# 🎯 환경 설정
# =============================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

# =============================
# 🎧 Celery + Redis 연결
# =============================
celery = Celery('analyzer', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

@celery.task
def analyze_text():
    """
    💡 text_queue에서 텍스트를 가져와 transformers pipeline으로 감정 분석
    → 결과를 DB에 저장 + redis result_channel로 publish
    """
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        text_bytes = r.rpop("text_queue")
        if not text_bytes:
            return  # queue가 비어있으면 종료

        text = text_bytes.decode("utf-8")

        # Huggingface transformers 감정분석 pipeline
        classifier = pipeline("sentiment-analysis")
        result = classifier(text)[0]
        emotion = result['label']

        # SQLite DB에 저장
        with sqlite3.connect("results.db") as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS results (text TEXT, emotion TEXT)"
            )
            conn.execute(
                "INSERT INTO results VALUES (?, ?)",
                (text, emotion)
            )
            conn.commit()

        # 분석 결과를 redis result_channel로 publish
        r.publish("result_channel", f"{text} → {emotion}")
        print(f"✅ 분석 결과 → {text} → {emotion}")

    except Exception as e:
        print(f"❌ analyzer 오류: {e}")
