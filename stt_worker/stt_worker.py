import os
import redis
import numpy as np
from scipy.io.wavfile import write
import whisper as openai_whisper
from celery import Celery
import tempfile

# ✅ Redis 설정
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
celery = Celery("stt_worker", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# ✅ Whisper 모델 로드
model_size = os.getenv("MODEL_SIZE", "base")
model_path = os.getenv("MODEL_PATH", "/app/models")
os.makedirs(model_path, exist_ok=True)
model = openai_whisper.load_model(model_size, download_root=model_path)

@celery.task(name="stt_worker.transcribe_audio", queue="stt_queue")
def transcribe_audio(audio_bytes):
    print("FastAPI → Celery 전달 audio_chunk 수신")

    # ✅ 1. int16 array로 바로 변환
    audio_np_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

    # ✅ 2. WAV 파일로 저장 후 Whisper STT 수행
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
        write(tmpfile.name, 16000, audio_np_int16)   # 16kHz, int16 PCM
        result = model.transcribe(tmpfile.name, language="ko", fp16=False)

    text = result.get("text", "").strip()
    print(f"[STT] 🎙️ Whisper STT 결과: {text}")

    # ✅ 3. analyzer_worker 호출
    celery.send_task(
        "analyzer_worker.analyzer_text",
        args=[text],
        queue="analyzer_queue"
    )
    print(f"[STT] ✅ analyzer_worker 호출 완료: {text}")