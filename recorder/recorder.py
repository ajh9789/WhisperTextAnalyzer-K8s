
# ========================
# ✅ recorder/recorder.py 개선 버전
# ========================

import os
import numpy as np
import sounddevice as sd
import redis
from scipy.signal import resample_poly

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

SAMPLE_RATE = 16000
RECORD_SECONDS = 3
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0007))

def record_audio():
    print(f"recorder 연결 Redis host: {REDIS_HOST}")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    print("녹음 시작")
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()

    energy = np.mean(np.abs(audio))
    print(f"평균 에너지: {energy}")

    if energy < ENERGY_GATE_THRESHOLD:
        print("무음 → 전송 생략")
        return

    audio_resampled = resample_poly(audio.flatten(), 1, 1)
    r.lpush("audio_queue", audio_resampled.tobytes())
    r.lpush("celery", '')  # dummy task trigger 용 (원래는 필요 없음)
    r.publish("text_channel", b"dummy")  # optional dummy publish (test)

    print("오디오 전송 완료")

if __name__ == "__main__":
    while True:
        record_audio()
