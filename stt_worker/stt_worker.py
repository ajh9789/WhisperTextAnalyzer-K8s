# stt_worker/stt_worker.py → celery worker 사용 X → while loop 실행용으로만 변경

import os
import numpy as np
import redis
import whisper

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

model_size = os.getenv("MODEL_SIZE", "tiny")
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
    print("🚀 STT Worker started.")
    while True:
        transcribe_audio()