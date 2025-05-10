from celery import Celery
import redis
import sqlite3
from transformers import pipeline

app = Celery('analyzer', broker='redis://redis:6379/0')
r = redis.Redis(host="redis", port=6379)
classifier = pipeline("sentiment-analysis")

# ✅ SQLite 초기화
conn = sqlite3.connect("results.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS results (text TEXT, emotion TEXT)")
conn.commit()

# 🎯 Celery Task: 텍스트 감정 분석 + DB 저장 + Pub/Sub
@app.task
def analyze_text():
    text = r.rpop("text_queue")
    if not text:
        return
    emotion = classifier(text.decode())[0]['label']
    c.execute("INSERT INTO results VALUES (?, ?)", (text.decode(), emotion))
    conn.commit()
    r.publish("result_channel", f"{text.decode()} → {emotion}")

# ✅ Celery Worker만 실행
# docker-compose exec analyzer_worker celery -A worker worker --loglevel=info
