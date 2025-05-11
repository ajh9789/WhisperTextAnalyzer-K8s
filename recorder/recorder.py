# =============================================
# ✅ recorder/recorder.py 개선 버전
# =============================================
import os
import numpy as np
import sounddevice as sd
import redis
from scipy.signal import resample_poly

# 🎯 DOCKER 환경변수 유무로 판단
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

SAMPLE_RATE = 16000
RECORD_SECONDS = 5
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0001))
DEVICE_ID = 7  # 🎙️ 로컬 테스트용 mic index

def record_audio():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    print(f"🎙️ Recording from device {DEVICE_ID}...")
    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32',
        device=DEVICE_ID
    )
    sd.wait()

    energy = np.mean(np.abs(audio))
    print(f"🔎 Energy: {energy}")
    if energy < ENERGY_GATE_THRESHOLD:
        print("⚠️ Low energy detected, skipping frame.")
        return

    audio_resampled = resample_poly(audio.flatten(), 1, 1)
    r.lpush("audio_queue", audio_resampled.tobytes())
    print("✅ Audio pushed to audio_queue.")

if __name__ == "__main__":
    while True:
        record_audio()
