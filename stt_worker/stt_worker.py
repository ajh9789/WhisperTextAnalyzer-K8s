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

# ✅ 메모리 내 4초 누적 버퍼 (단일 사용자 전용)
buffer = []

@celery.task(name="stt_worker.transcribe_audio", queue="stt_queue")
def transcribe_audio(audio_bytes):
    global buffer

    print("[STT] 🎧 오디오 청크 수신")
    buffer.append(np.frombuffer(audio_bytes, dtype=np.int16))

    if len(buffer) < 4:
        print(f"[STT] ⏳ 누적 {len(buffer)}/4...")
        return

    # ✅ 4초 누적 완료 → Whisper 분석
    combined = np.concatenate(buffer[:8])  # 최대 4초까지만 자름

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
        write(tmpfile.name, 16000, combined.astype(np.int16))
        result = model.transcribe(tmpfile.name, language="ko", fp16=False)

    text = result.get("text", "").strip()
    print(f"[STT] 🎙️ Whisper STT 결과: {text}")

    if not text:
        print("[STT] ⚠️ 공백 텍스트 → 분석 생략")
        buffer.clear()
        return "[STT] ⚠️ 생략됨"

    # ✅ 감정 분석기로 전달
    celery.send_task(
        "analyzer_worker.analyzer_text",
        args=[text],
        queue="analyzer_queue"
    )
    print("[STT] ✅ analyzer_worker 호출 완료")

    # ✅ 버퍼 초기화
    buffer.clear()