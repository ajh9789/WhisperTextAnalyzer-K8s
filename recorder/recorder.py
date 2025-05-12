# =============================================
# ✅ recorder/recorder.py (개선판)
# =============================================

import os
import numpy as np
import sounddevice as sd
import redis
from scipy.signal import resample_poly

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

SAMPLE_RATE = 16000
RECORD_SECONDS = 5
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0001))
DEVICE_ID = 7

def record_audio():
    """
    마이크에서 오디오 녹음 후 Redis audio_queue로 push.
    에너지 게이트 필터링으로 무음 제거.
    """
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    print(f"🎙️ Recording from device {DEVICE_ID}...")
    try:
        # ✅ 마이크 녹음 시작
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            device=DEVICE_ID
        )
        sd.wait()
    except Exception as e:
        print(f"❌ Recorder error: {e}")
        return

    # ✅ 녹음 에너지 체크 (noise filter)
    energy = np.mean(np.abs(audio))
    print(f"🔎 Energy: {energy}")
    if energy < ENERGY_GATE_THRESHOLD:
        print("⚠️ Low energy detected, skipping frame.")
        return

    # ✅ 오디오 flatten + push
    try:
        audio_resampled = resample_poly(audio.flatten(), 1, 1)
        r.lpush("audio_queue", audio_resampled.tobytes())
        print("✅ Audio pushed to audio_queue.")
    except Exception as e:
        print(f"❌ Redis push error: {e}")

if __name__ == "__main__":
    while True:
        record_audio()
