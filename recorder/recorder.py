# ==============================
# ✅ recorder.py : local mic → redis audio_queue
# ==============================

import os
import sounddevice as sd
import numpy as np
import redis
from scipy.signal import resample_poly
import traceback

# Redis 연결 정보 설정
#REDIS_HOST = "redis"  # docker-compose 기준 redis 서비스 이름
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = 6379

# 오디오 녹음 설정
DEVICE_ID = int(os.getenv("DEVICE_ID", 14))
RECORD_SECONDS = 5
CHANNELS = 1
ENERGY_GATE_THRESHOLD = 0.001

# Redis 연결 확인
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    r.ping()
except redis.ConnectionError:
    print("❌ Redis 연결 실패!")
    exit(1)

# 마이크 디바이스 정보 확인
try:
    device_info = sd.query_devices(DEVICE_ID, 'input')
except Exception as e:
    print(f"❌ 오디오 장치 오류: {e}")
    exit(1)

SAMPLE_RATE = int(device_info['default_samplerate'])
print(f"🎙️ Recorder 시작 - {device_info['name']} ({SAMPLE_RATE} Hz)")

def record_and_send():
    try:
        audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32', device=DEVICE_ID)
        sd.wait()
        audio = np.squeeze(audio)
        if np.mean(np.abs(audio)) < ENERGY_GATE_THRESHOLD:
            print("🔕 무음 → 전송 생략")
            return
        if SAMPLE_RATE != 16000:
            audio = resample_poly(audio, up=16000, down=SAMPLE_RATE)
        r.lpush("audio_queue", audio.astype(np.float32).tobytes())
        print("✅ 오디오 전송 완료")
    except Exception as e:
        print(e)
        traceback.print_exc()

if __name__ == "__main__":
    while True:
        record_and_send()
