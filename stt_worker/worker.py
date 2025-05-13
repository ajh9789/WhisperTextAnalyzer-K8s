import os
import redis
import numpy as np
from scipy.io.wavfile import write
import whisper as openai_whisper
from celery import Celery
import tempfile

# ✅ Redis 연결 정보 설정
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

# ✅ Celery + Redis 연결
celery_app = Celery("stt_worker", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# ✅ Whisper 모델 로드
model_size = os.getenv("MODEL_SIZE", "small")
model_path = os.getenv("MODEL_PATH", "/app/models")
os.makedirs(model_path, exist_ok=True)
model = openai_whisper.load_model(model_size, download_root=model_path)

@celery_app.task
def transcribe_audio():
    """
    Redis audio_queue에서 PCM bytes를 가져와 WAV로 변환 후 Whisper STT 수행.
    결과 텍스트를 text_queue로 push.
    """
    print("[STT] ⏳ polling audio_queue...")
    try:
        # ✅ Redis audio_queue에서 데이터 가져오기
        audio_bytes = r.rpop("audio_queue")
        if not audio_bytes:
            print("[STT] 💤 queue empty")
            return

        print(f"[STT] ✅ pulled {len(audio_bytes)} bytes from Redis")

        # ✅ PCM bytes → numpy array로 변환 (float32)
        audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

        # ✅ 임시 WAV 파일로 저장 → Whisper는 파일을 요구
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
            write(tmpfile.name, 16000, audio_np)  # FastAPI 기준 16kHz로 고정
            # ✅ Whisper STT 수행
            result = model.transcribe(tmpfile.name, language="ko", fp16=False)

        # ✅ 결과 텍스트 추출
        text = result.get("text", "").strip()
        print(f"[STT] 🎙️ Whisper result: {text}")

        # ✅ 결과 텍스트 Redis text_queue에 push
        r.lpush("text_queue", text.encode())
        print(f"[STT] ✅ pushed to text_queue: {text}")

    except Exception as e:
        print(f"[STT] ❌ Error: {e}")
