# ========================
# ✅ stt_worker/stt_worker.py 개선 완전체
# ========================

import numpy as np
import redis
import whisper
import torch
from celery import Celery
import os

# ========================
# 🎯 설정값
# ========================

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"  # ⭐ Celery와 redis 동기화

# ========================
# 🎯 Celery + Redis client 설정
# ========================

celery = Celery('stt', broker=BROKER_URL)
r = redis.Redis.from_url(BROKER_URL)  # ⭐ broker url 그대로 사용 → 절대 mismatch 안 됨

print(f"stt_worker 연결 Redis: {BROKER_URL}")

# ========================
# 🎯 Whisper 모델 설정
# ========================

MODEL_SIZE = "small"
model_instance = None

def get_model():
    global model_instance
    if model_instance is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Whisper 모델 로드 중... (device: {device})")
        model_instance = whisper.load_model(MODEL_SIZE, device=device)
    return model_instance

# ========================
# 🎯 Celery Task
# ========================

@celery.task(name="stt.transcribe_audio")
def transcribe_audio():
    try:
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            print("stt_worker: audio_queue 비어있음")
            return

        print("stt_worker: audio_queue 데이터 수신 → STT 시작")
        audio = np.frombuffer(audio_bytes, dtype=np.float32)

        result = get_model().transcribe(
            audio,
            language="ko",
            fp16=(torch.cuda.is_available()),
            temperature=0,
            condition_on_previous_text=False
        )

        text = result['text']
        r.lpush("text_queue", text.encode("utf-8"))
        r.publish("text_channel", text)

        print(f"[STT 완료] 텍스트: {text}")

    except Exception as e:
        print(f"STT 오류: {e}")