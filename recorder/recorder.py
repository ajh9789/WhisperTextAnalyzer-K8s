"""
WhisperTextAnalyzer - Recorder Module
-------------------------------------
🎙️ 시스템에서 실시간으로 오디오를 녹음하고, 녹음된 데이터를 Redis Queue로 전송하는 모듈입니다.
Whisper 모델의 입력 요구 사항(16kHz, mono, float32)에 맞게 resample 처리도 수행합니다.
"""

import sounddevice as sd
import numpy as np
import redis
from scipy.signal import resample_poly

# ================================
# 🎯 Redis 설정
# ================================
REDIS_HOST = "redis"  # docker-compose 기준 redis 서비스 이름
REDIS_PORT = 6379  # Redis 기본 포트

# ================================
# 🎯 녹음 설정
# ================================
DEVICE_ID = 14  # 사용할 마이크 device index (사용자 환경에 맞게 설정)
RECORD_SECONDS = 5  # 녹음 시간 (초)
CHANNELS = 1  # mono 녹음
ENERGY_GATE_THRESHOLD = 0.001  # 민감도: 평균 진폭이 threshold 미만이면 무시

# ================================
# 🎯 Redis 연결 객체 생성
# ================================
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# ================================
# 🎧 오디오 디바이스 정보 확인
# ================================
device_info = sd.query_devices(DEVICE_ID, 'input')
SAMPLE_RATE = int(device_info['default_samplerate'])  # 선택된 디바이스의 기본 샘플레이트 확인

print(f"🎙️ Recorder 시작 - Device {DEVICE_ID}: {device_info['name']} / {SAMPLE_RATE} Hz")
print(f"🔧 민감도 threshold: {ENERGY_GATE_THRESHOLD}, 녹음 시간: {RECORD_SECONDS}초")


# ================================
# 🎙️ 오디오 녹음 + Redis 전송 함수
# ================================
def record_and_send_to_redis():
    """
    실시간으로 오디오 데이터를 녹음하고 Whisper 모델에 적합하도록 전처리 후 Redis Queue로 전송합니다.

    주요 흐름:
    1. sounddevice로 녹음
    2. 평균 진폭 필터 (무음 제거)
    3. Whisper 모델 요구 스펙 (16kHz, float32)로 resample
    4. Redis Queue로 바이너리 데이터 전송
    """
    try:
        # 🎙️ 오디오 녹음
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='float32',
            device=DEVICE_ID
        )
        sd.wait()  # 녹음 완료 대기
        audio = np.squeeze(audio)  # stereo → mono (1D array)

        # ✅ 민감도 필터링: 무음 구간 방지
        avg_amplitude = np.mean(np.abs(audio))
        if avg_amplitude < ENERGY_GATE_THRESHOLD:
            print("🔕 무음 감지 → 데이터 전송 생략")
            return

        # ✅ Whisper 입력 스펙으로 resample
        if SAMPLE_RATE != 16000:
            # scipy resample_poly 사용: aliasing 최소화 + 고속 처리
            audio = resample_poly(audio, up=16000, down=SAMPLE_RATE)

        # ✅ Redis로 바이너리 데이터 전송
        r.lpush("audio_queue", audio.astype(np.float32).tobytes())
        print(f"✅ {RECORD_SECONDS}초 오디오 chunk 전송 완료 (Queue: audio_queue)")

    except Exception as e:
        # 예외 발생 시 로깅
        print(f"❌ 예외 발생: {str(e)}")


# ================================
# 🎯 메인 루프 (무한 녹음)
# ================================
if __name__ == "__main__":
    print("🎬 Whisper Recorder 프로세스 시작 (Ctrl+C로 종료)")
    try:
        while True:
            record_and_send_to_redis()
    except KeyboardInterrupt:
        print("\n🛑 사용자 종료 요청 → 프로그램 종료")