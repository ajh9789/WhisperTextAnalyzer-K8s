import os
import io
import redis
import whisper as openai_whisper
from celery import Celery

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
    """
    Redis audio_queue에서 오디오 데이터를 가져와 Whisper로 STT 후 text_queue에 결과 push
    """
    print("[STT] ⏳ polling audio_queue...")
    try:
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            print("[STT] 💤 queue empty")
            return

        print(f"[STT] ✅ pulled {len(audio_bytes)} bytes from Redis")

        # Whisper는 WAV file stream을 기대 → io.BytesIO 그대로 전달
        result = model.transcribe(io.BytesIO(audio_bytes), language="ko", fp16=False)
        text = result.get("text", "").strip()
        print(f"[STT] 🎙️ Whisper result: {text}")

        # 결과를 text_queue에 push
        r.lpush("text_queue", text.encode())
        print(f"[STT] ✅ pushed to text_queue: {text}")

    except Exception as e:
        print(f"[STT] ❌ Error: {e}")