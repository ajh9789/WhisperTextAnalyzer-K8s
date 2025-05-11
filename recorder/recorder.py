# ========================
# 🎙️ Whisper Text Analyzer - Recorder 서비스
# 🎙️ 마이크 입력 → audio_queue (Redis)로 전송
# ========================

import os
import numpy as np
import sounddevice as sd
import redis
from scipy.signal import resample_poly

# ========================
# 🎯 Redis 연결 설정
# ========================

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

# ========================
# 🎯 녹음 기본 설정
# ========================

SAMPLE_RATE = 16000            # 녹음 샘플레이트 (Hz)
RECORD_SECONDS = 5             # 녹음 시간 (초)
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0005))  # 무음 필터 민감도

def record_audio():
    """
    마이크로부터 오디오를 녹음하고 Redis audio_queue로 전송.
    (무음이면 데이터 전송을 생략)
    """
    print(f"✅ recorder 연결 Redis host: {REDIS_HOST}")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    print("🎙️ 녹음 시작")
    # numpy float32 형태로 녹음
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()  # 녹음 종료 대기

    # 평균 에너지로 무음 여부 판단
    energy = np.mean(np.abs(audio))
    print(f"ℹ️ 평균 에너지: {energy}")

    if energy < ENERGY_GATE_THRESHOLD:
        print("⚠️ 무음 → 전송 생략")
        return

    # 오디오 데이터 재샘플링 (현재는 그대로 사용, 추후 개선 가능)
    audio_resampled = resample_poly(audio.flatten(), 1, 1)

    # Redis queue + test dummy publish
    r.lpush("audio_queue", audio_resampled.tobytes())
    r.publish("text_channel", b"dummy")  # 🎯 optional dummy publish (리스너 작동 확인용)
    print("✅ 오디오 전송 완료 (audio_queue + dummy publish)")

if __name__ == "__main__":
    # 무한 루프: 계속 녹음 → queue 전송
    while True:
        record_audio()
