
import os
import numpy as np
import sounddevice as sd
import redis
from scipy.signal import resample_poly

# ✅ Redis 연결 정보 설정
REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

# ✅ 오디오 녹음 설정
SAMPLE_RATE = 16000           # Whisper와 일치 → 16kHz
RECORD_SECONDS = 5            # 5초 단위 녹음
ENERGY_GATE_THRESHOLD = float(os.getenv("ENERGY_THRESHOLD", 0.0001))
DEVICE_ID = None              # ✅ None → 기본 마이크 사용

def get_redis_connection():
    """
    Redis 연결을 시도하고 실패 시 None 반환.
    """
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        r.ping()
        print("✅ Redis 연결 성공")
        return r
    except redis.ConnectionError as e:
        print(f"❌ Redis 연결 실패: {e}")
        return None

def record_audio(redis_conn):
    """
    마이크로부터 오디오를 녹음하고 energy threshold를 체크 후
    Redis audio_queue로 push.
    """
    print(f"\n🎙️ Recording from device {DEVICE_ID}...")
    try:
        # ✅ 오디오 녹음
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            device=DEVICE_ID
        )
        sd.wait()
    except Exception as e:
        print(f"❌ 마이크 녹음 실패: {e}")
        return

    # ✅ 무음 필터링
    energy = np.mean(np.abs(audio))
    print(f"🔎 에너지: {energy}")
    if energy < ENERGY_GATE_THRESHOLD:
        print("⚠️ 무음으로 판단 → frame 건너뜀")
        return

    try:
        # ✅ numpy array → PCM bytes로 변환
        audio_resampled = resample_poly(audio.flatten(), 1, 1)  # 그대로 pass
        redis_conn.lpush("audio_queue", audio_resampled.tobytes())
        print("✅ 오디오 Redis audio_queue 전송 완료")
    except Exception as e:
        print(f"❌ Redis 전송 실패: {e}")

if __name__ == "__main__":
    # ✅ main 루프
    redis_conn = get_redis_connection()
    if not redis_conn:
        print("❌ Redis 연결 실패 → 프로그램 종료")
        exit(1)

    print("🎧 Recorder 서비스 시작 (Ctrl+C로 중지)")
    try:
        while True:
            record_audio(redis_conn)
    except KeyboardInterrupt:
        print("\n🛑 프로그램 종료 (Ctrl+C)")