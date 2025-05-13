import os
import redis
import numpy as np
from scipy.io.wavfile import write
import whisper as openai_whisper
from celery import Celery
import tempfile

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

celery_app = Celery("stt_worker", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

model_size = os.getenv("MODEL_SIZE", "small")
model_path = os.getenv("MODEL_PATH", "/app/models")
os.makedirs(model_path, exist_ok=True)
model = openai_whisper.load_model(model_size, download_root=model_path)

@celery_app.task
def transcribe_audio():
    print("[STT] ⏳ audio_queue polling 시작")
    try:
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            print("[STT] 💤 audio_queue 비어있음")
            return

        print(f"[STT] ✅ pulled {len(audio_bytes)} bytes from Redis")
        audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
            write(tmpfile.name, 16000, audio_np)
            result = model.transcribe(tmpfile.name, language="ko", fp16=False)

        text = result.get("text", "").strip()
        print(f"[STT] 🎙️ Whisper STT 결과: {text}")

        r.lpush("text_queue", text.encode())
        print(f"[STT] ✅ text_queue에 push 완료: {text}")

    except Exception as e:
        print(f"[STT] ❌ Error: {e}")
