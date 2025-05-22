import os
import numpy as np
from scipy.io.wavfile import write
import whisper as openai_whisper
from celery import Celery
import tempfile

# ✅ 기본 설정
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
celery = Celery("stt_worker", broker=f"redis://{REDIS_HOST}:6379/0")

# ✅ Whisper 모델 로드
model_size = os.getenv("MODEL_SIZE", "tiny")
model_path = os.getenv("MODEL_PATH", "/app/models")
os.makedirs(model_path, exist_ok=True)
model = openai_whisper.load_model(model_size, download_root=model_path)


@celery.task(name="stt_worker.transcribe_audio", queue="stt_queue")
def transcribe_audio(audio_bytes):
    print("[STT] 🎧 오디오 청크 수신")
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
        write(
            tmpfile.name,
            16000,
            np.frombuffer(audio_bytes, dtype=np.int16).astype(np.int16),
        )
        try:
            result = model.transcribe(tmpfile.name, language="ko", fp16=False)
            text = result.get("text", "").strip()
            if not text:
                print("[STT] ⚠️ 공백 텍스트 → 분석 생략")
                return
            print(f"[STT] 🎙️ Whisper STT 결과: {text}")
        except Exception as e:
            print(f"[STT] ❌ Whisper 처리 실패: {e}")
            return

        try:
            celery.send_task(
                "analyzer_worker.analyzer_text", args=[text], queue="analyzer_queue"
            )
            print("[STT] ✅ analyzer_worker 호출 완료")
        except Exception as e:
            print(f"[STT] ❌ analyzer_worker 호출 실패: {e}")
