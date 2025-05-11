# =============================================
# ✅ stt_worker/stt_worker.py
# =============================================

import numpy as np
import redis
import whisper
import torch
from celery import Celery
import os

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
celery = Celery('stt', broker=BROKER_URL)
r = redis.Redis.from_url(BROKER_URL)

MODEL_SIZE = "small"
model_instance = None

def get_model():
    global model_instance
    if model_instance is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_instance = whisper.load_model(MODEL_SIZE, device=device)
    return model_instance

@celery.task(name="stt.transcribe_audio")
def transcribe_audio():
    audio_bytes = r.rpop("audio_queue")
    if not audio_bytes:
        return

    audio = np.frombuffer(audio_bytes, dtype=np.float32)
    result = get_model().transcribe(audio, language="ko", fp16=(torch.cuda.is_available()), temperature=0, condition_on_previous_text=False)
    text = result['text']

    r.lpush("text_queue", text.encode("utf-8"))
    r.publish("text_channel", text)