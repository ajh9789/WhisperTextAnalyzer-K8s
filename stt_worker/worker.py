import os
import io
import numpy as np
import redis
import whisper as openai_whisper
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

celery_app = Celery("stt_worker", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

#언젠가 쓸 환경변수 사용을 위해 미리사용해보
model_size = os.getenv("MODEL_SIZE", "tiny")
model_path = os.getenv("MODEL_PATH", "/app/models")
os.makedirs(model_path, exist_ok=True)   # ✅ 폴더 자동 생성
model = openai_whisper.load_model(model_size, download_root=model_path)

@celery_app.task
def transcribe_audio():
    """
    Redis audio_queue에서 오디오 데이터를 가져와 Whisper STT로 텍스트 변환 후 text_queue에 push
    """
    print("[STT] ⏳ polling audio_queue...")
    try:
        audio_bytes = r.rpop("audio_queue")
        if audio_bytes:
            print(f"✅ pulled {len(audio_bytes)} bytes from Redis")
            try:
                result = model.transcribe(io.BytesIO(audio_bytes))
                print(f"🎙️ Whisper result: {result['text']}")
            except Exception as e:
                print(f"❌ Whisper decode error: {e}")
        else:
            print("❌ No data pulled from Redis")
    except Exception as e:
        print(f"[STT] Redis error: {e}")
        return

    if not audio_bytes:
        print("[STT] 💤 queue empty")
        return

    print("[STT] 🎙️ audio found, transcribing...")
    try:
        audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
        result = model.transcribe(audio_np, language="ko", fp16=False)
        text = result["text"]
    except Exception as e:
        print(f"[STT] Whisper error: {e}")
        return

    try:
        r.lpush("text_queue", text.encode())
        print(f"[STT] ✅ pushed to text_queue: {text}")
    except Exception as e:
        print(f"[STT] Redis push error: {e}")
