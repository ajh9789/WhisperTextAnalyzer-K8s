# ✅ stt_worker.py 개선 버전
import numpy as np
import redis
import whisper
import torch
from celery import Celery
import os

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

celery = Celery('stt', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

# 🎯 Whisper 모델을 global로 미리 로드
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("small", device=device)
print(f"✅ Whisper 모델 로드 완료 (device: {device})")

@celery.task(name="stt.transcribe_audio")
def transcribe_audio():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            return

        audio = np.frombuffer(audio_bytes, dtype=np.float32)
        result = model.transcribe(audio, language="ko", fp16=(device == "cuda"),
                                  temperature=0, condition_on_previous_text=False)

        text = result['text']
        print(f"📥 STT 추출 텍스트: {text}")
        r.lpush("text_queue", text.encode("utf-8"))
        r.publish("text_channel", text)
    except Exception as e:
        print(f"❌ STT 오류: {e}")
