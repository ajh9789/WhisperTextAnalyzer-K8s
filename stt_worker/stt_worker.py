# =============================================
# ✅ stt_worker/stt_worker.py 개선 버전
# =============================================
import os
import numpy as np
import redis
import whisper
from celery import Celery

# 🎯 DOCKER 환경변수 유무로 판단
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

app = Celery('stt_worker', broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

model_size = os.getenv("MODEL_SIZE", "small")
model = whisper.load_model(model_size)

@app.task
def transcribe_audio():
    print("[STT] polling audio_queue...")
    audio_bytes = r.rpop("audio_queue")
    if not audio_bytes:
        print("[STT] queue empty.")
        return

    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
    result = model.transcribe(audio_np, language="ko", fp16=False)
    text = result['text']

    r.lpush("text_queue", text.encode())
    print(f"✅ Transcribed text pushed to text_queue: {text}")

if __name__ == "__main__":
    while True:
        transcribe_audio()