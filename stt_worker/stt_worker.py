# ========================
# 🎙️ Whisper Text Analyzer - STT Worker 서비스
# 🎙️ audio_queue → Whisper STT → text_queue + text_channel
# ========================

import numpy as np
import redis
import whisper
import torch
from celery import Celery
import os

# ========================
# 🎯 Redis + Celery 브로커 설정
# ========================

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Celery 인스턴스 생성 (브로커=Redis)
celery = Celery('stt', broker=BROKER_URL)

# Redis 클라이언트 (Celery와 동일 브로커 사용 → mismatch 방지)
r = redis.Redis.from_url(BROKER_URL)

print(f"✅ stt_worker 연결 Redis: {BROKER_URL}")

# ========================
# 🎯 Whisper 모델 설정
# ========================

MODEL_SIZE = "small"  # small: 빠르고 적절한 정확도 / medium, large 가능
model_instance = None  # 싱글톤 패턴으로 모델 1회만 로드

def get_model():
    """
    Whisper 모델을 로드하여 반환 (최초 1회만 로드)
    """
    global model_instance
    if model_instance is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🎯 Whisper 모델 로드 중... (device: {device})")
        model_instance = whisper.load_model(MODEL_SIZE, device=device)
    return model_instance

# ========================
# 🎯 Celery Task 정의
# ========================

@celery.task(name="stt.transcribe_audio")
def transcribe_audio():
    """
    audio_queue → STT → text_queue + text_channel로 텍스트 전송
    """
    try:
        # Redis audio_queue에서 오디오 데이터 수신
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            print("⚠️ stt_worker: audio_queue 비어있음 → 대기")
            return

        print("🎙️ stt_worker: audio_queue 데이터 수신 → STT 시작")

        # numpy 배열로 변환
        audio = np.frombuffer(audio_bytes, dtype=np.float32)

        # Whisper STT 수행
        result = get_model().transcribe(
            audio,
            language="ko",  # 한국어 고정
            fp16=(torch.cuda.is_available()),
            temperature=0,
            condition_on_previous_text=False
        )

        text = result['text']

        # STT 결과를 Redis로 전송
        r.lpush("text_queue", text.encode("utf-8"))
        r.publish("text_channel", text)

        print(f"✅ [STT 완료] 텍스트: {text}")

    except Exception as e:
        print(f"❌ STT 오류: {e}")
