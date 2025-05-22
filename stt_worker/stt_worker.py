import os
import re
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


# ✅ 반복 텍스트 필터 함수
def is_repetitive(text: str) -> bool:
    # 공백 제거 후 문자 반복 (예: 아아아아아아)
    if re.fullmatch(r"(.)\1{4,}", text.replace(" ", "")):
        return True
    # 단어 반복 (예: 좋아요 좋아요 좋아요 ...)
    if re.search(r"\b(\w+)\b(?: \1){4,}", text):
        return True
    # 음절 반복 (예: 아 아 아 아 아 ...)
    if re.fullmatch(r"(.)\s*(?:\1\s*){4,}", text):
        return True
    return False


@celery.task(name="stt_worker.transcribe_audio", queue="stt_queue")
def transcribe_audio(audio_bytes):
    global buffer

    print("[STT] 🎧 오디오 청크 수신")
    buffer.append(np.frombuffer(audio_bytes, dtype=np.int16))

    if len(buffer) < 8:
        print(f"[STT] ⏳ 누적 {len(buffer)}/8...")
        return

    combined = np.concatenate(buffer[:8])
    buffer.clear()  #

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmpfile:
        write(tmpfile.name, 16000, combined.astype(np.int16))
        try:
            result = model.transcribe(tmpfile.name, language="ko", fp16=False)
            text = result.get("text", "").strip()

            if not text:
                print("[STT] ⚠️ 공백 텍스트 → 분석 생략")
                buffer.clear()
                return

            if is_repetitive(text):
                print(f"[STT] ⚠️ 반복 텍스트 감지 → 분석 생략: {text}")
                buffer.clear()
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
