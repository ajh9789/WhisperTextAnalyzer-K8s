# =============================================
# ✅ recorder/recorder.py
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
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0005))
DEVICE_ID = 7 #로컬연습용마이크
def record_audio():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    audio = sd.rec( #로컬연습용
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32',
        device=DEVICE_ID
    )
    #audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()

    energy = np.mean(np.abs(audio))
    if energy < ENERGY_GATE_THRESHOLD:
        return

    audio_resampled = resample_poly(audio.flatten(), 1, 1)
    r.lpush("audio_queue", audio_resampled.tobytes())
    r.publish("text_channel", b"dummy")

if __name__ == "__main__":
    while True:
        record_audio()