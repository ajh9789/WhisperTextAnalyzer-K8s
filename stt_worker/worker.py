from celery import Celery
import redis
import numpy as np
import whisper

# Celery 설정
app = Celery('stt', broker='redis://redis:6379/0')

r = redis.Redis(host="redis", port=6379)
model = whisper.load_model("small", device="cuda")

# 🎯 Celery Task: Redis audio_queue → Whisper STT → text_queue로 전달
@app.task
def transcribe_audio():
    audio_bytes = r.rpop("audio_queue")
    if not audio_bytes:
        return
    audio = np.frombuffer(audio_bytes, dtype=np.float32)
    result = model.transcribe(
        audio,
        language="ko",
        fp16=True,  # ✅ GPU 사용으로 속도 + 메모리 최적화
        temperature=0,  # ✅ 예측 일관성 확보 (Deterministic output)
        condition_on_previous_text=False  # ✅ 실시간 chunk 처리 시 필수 (Context 오류 방지)
    )
    r.lpush("text_queue", result['text'])

# ✅ Celery Worker만 실행 (Multi Worker 대응)
# docker-compose exec stt_worker celery -A worker worker --loglevel=info

