# =============================================
# ✅ 최종 개선: 실험 + 발표용 standalone polling 버전 (tiny 기준)
# =============================================

# recorder/recorder.py → 그대로 (정상)
# listener/listener.py → 그대로 (정상)

# ✅ stt_worker/stt_worker.py

import os
import numpy as np
import redis
import whisper

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

model_size = "tiny"  # ✅ 발표용 tiny 모델 고정
model = whisper.load_model(model_size)

def transcribe_audio():
    print("[STT] ⏳ polling audio_queue...")
    audio_bytes = r.rpop("audio_queue")
    if not audio_bytes:
        print("[STT] 💤 queue empty")
        return

    print("[STT] 🎙️ audio found, transcribing...")
    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
    result = model.transcribe(audio_np, language="ko", fp16=False)
    text = result['text']

    r.lpush("text_queue", text.encode())
    print(f"[STT] ✅ pushed to text_queue: {text}")

if __name__ == "__main__":
    print("🚀 STT Worker (tiny) started.")
    while True:
        transcribe_audio()