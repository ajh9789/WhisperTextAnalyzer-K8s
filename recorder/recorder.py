# ✅ recorder/recorder.py : local mic → redis audio_queue + stt_worker task 호출

import os
import sounddevice as sd
import numpy as np
import redis
from scipy.signal import resample_poly
from celery import Celery

# =============================
# 🎯 환경 설정
# =============================
REDIS_HOST = os.getenv("REDIS_HOST", "redis")     # 도커에서는 "redis" 서비스명
REDIS_PORT = 6379
DEVICE_ID = int(os.getenv("DEVICE_ID", 14))
RECORD_SECONDS = 5
CHANNELS = 1
ENERGY_GATE_THRESHOLD = 0.001

# =============================
# 🎧 Redis + Celery 연결
# =============================
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
celery_app = Celery(broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0')

# =============================
# 🎧 오디오 디바이스 설정
# =============================
device_info = sd.query_devices(DEVICE_ID, 'input')
SAMPLE_RATE = int(device_info['default_samplerate'])
print(f"🎙️ Recorder 시작: {device_info['name']} ({SAMPLE_RATE} Hz)")

def record_and_send():
    """
    🎙️ 마이크로부터 음성을 녹음하고 redis audio_queue로 전송
    → 무음은 생략
    → STT worker celery task 호출
    """
    try:
        # 녹음
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            device=DEVICE_ID
        )
        sd.wait()
        audio = np.squeeze(audio)

        # 무음 감지
        if np.mean(np.abs(audio)) < ENERGY_GATE_THRESHOLD:
            print("🔕 무음 → 전송 생략")
            return

        # Whisper 요구 샘플레이트로 변경
        if SAMPLE_RATE != 16000:
            audio = resample_poly(audio, up=16000, down=SAMPLE_RATE)

        # redis audio_queue로 전송
        r.lpush("audio_queue", audio.astype(np.float32).tobytes())
        print("✅ 오디오 전송 완료")

        # ✅ stt_worker celery task 호출 (컨테이너 구조 대응)
        celery_app.send_task("stt.transcribe_audio")

    except Exception as e:
        print(f"❌ Recorder 오류: {e}")

if __name__ == "__main__":
    # 무한 루프 → 실시간 녹음 + 전송 반복
    while True:
        record_and_send()
