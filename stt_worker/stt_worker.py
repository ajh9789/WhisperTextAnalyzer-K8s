import numpy as np
import redis
import whisper
import torch
from celery import Celery
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

app = Celery('stt', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

@app.task
def transcribe_audio():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            return
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("small", device=device)
        audio = np.frombuffer(audio_bytes, dtype=np.float32)
        result = model.transcribe(
            audio,
            language="ko",
            fp16=(device == "cuda"),
            temperature=0,
            condition_on_previous_text=False
        )
        r.lpush("text_queue", result['text'])
        print("✅ Whisper 변환 결과:", result['text'])
    except Exception as e:
        print(e)