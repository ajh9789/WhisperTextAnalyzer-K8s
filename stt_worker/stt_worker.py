# ✅ stt_worker/stt_worker.py : redis audio_queue → Whisper STT → redis text_queue + text_channel + analyzer task 호출

import numpy as np
import redis
import whisper
import torch
from celery import Celery
import os

# =============================
# 🎯 환경 설정
# =============================
REDIS_HOST = os.getenv("REDIS_HOST", "redis")  # 도커 컨테이너 이름
REDIS_PORT = 6379

# =============================
# 🎧 Celery + Redis 연결
# =============================
celery = Celery('stt', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')


@celery.task(name="stt.transcribe_audio")  # ✅ task 이름 반드시 지정
def transcribe_audio():
    """
    🎧 audio_queue에서 오디오를 가져와 Whisper STT로 변환 후
    → text_queue 저장
    → text_channel으로 실시간 STT 텍스트 broadcast
    → analyzer worker task 호출 (send_task 방식)
    """
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            return  # queue 비었으면 종료

        # Whisper 모델 로드
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("small", device=device)

        # 바이트 → numpy 배열로 복원
        audio = np.frombuffer(audio_bytes, dtype=np.float32)

        # STT 실행
        result = model.transcribe(
            audio,
            language="ko",
            fp16=(device == "cuda"),
            temperature=0,
            condition_on_previous_text=False
        )

        # 텍스트 결과 저장
        text = result['text']
        r.lpush("text_queue", text.encode("utf-8"))
        print(f"✅ STT 결과 → {text}")

        # 🎯 실시간 broadcast (listener에서 실시간 확인용)
        r.publish("text_channel", text)

        # ✅ analyzer worker task 호출 (컨테이너 환경 대응)
        celery.send_task("analyzer.analyze_text")

    except Exception as e:
        print(f"❌ STT 오류: {e}")
