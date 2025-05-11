import os
from celery import Celery
import redis
import sqlite3
from transformers import pipeline

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

app = Celery('analyzer', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

@app.task
def analyze_text():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        text = r.rpop("text_queue"
                      "")
        if not text:
            return
        classifier = pipeline("sentiment-analysis")
        emotion = classifier(text.decode())[0]['label']
        with sqlite3.connect("results.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS results (text TEXT, emotion TEXT)")
            conn.execute("INSERT INTO results VALUES (?, ?)", (text.decode(), emotion))
            conn.commit()
        r.publish("result_channel", f"{text.decode()} → {emotion}")
    except Exception as e:
        print(e)