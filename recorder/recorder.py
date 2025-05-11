# ✅ recorder.py 개선 버전
import os
import sounddevice as sd
import numpy as np
import redis
from scipy.signal import resample_poly
from celery import Celery

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
DEVICE_ID = int(os.getenv("DEVICE_ID", 14))
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", 5))
CHANNELS = 1
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0005))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
celery_app = Celery(broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

device_info = sd.query_devices(DEVICE_ID, 'input')
SAMPLE_RATE = int(device_info['default_samplerate'])
print(f"🎙️ Recorder 시작: {device_info['name']} ({SAMPLE_RATE} Hz)")

def record_and_send():
    try:
        audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                       channels=CHANNELS, dtype='float32', device=DEVICE_ID)
        sd.wait()
        audio = np.squeeze(audio)

        if np.mean(np.abs(audio)) < ENERGY_GATE_THRESHOLD:
            print("🔕 무음 → 전송 생략")
            return

        if SAMPLE_RATE != 16000:
            audio = resample_poly(audio, up=16000, down=SAMPLE_RATE)

        r.lpush("audio_queue", audio.astype(np.float32).tobytes())
        print("✅ 오디오 전송 완료")
        celery_app.send_task("stt.transcribe_audio")
    except Exception as e:
        print(f"❌ Recorder 오류: {e}")

if __name__ == "__main__":
    while True:
        record_and_send()
