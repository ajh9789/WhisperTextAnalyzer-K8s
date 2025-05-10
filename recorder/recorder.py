import sounddevice as sd
import numpy as np
import redis

# Redis 설정
REDIS_HOST = "redis"  # Docker 네트워크 내 Redis 컨테이너 이름
REDIS_PORT = 6379
DEVICE_ID = 14         # 🎙️ 사용할 마이크 device index
SAMPLE_RATE = 16000    # 🎙️ Whisper 모델 권장 샘플링
CHANNELS = 1
RECORD_SECONDS = 5     # 녹음 시간 (초)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# 🎙️ 오디오 녹음 및 Redis Queue로 전송 함수
def record():
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                   samplerate=SAMPLE_RATE,
                   channels=CHANNELS,
                   dtype='float32',
                   device=DEVICE_ID)
    sd.wait()
    audio = np.squeeze(audio).tobytes()
    r.lpush("audio_queue", audio)  # Redis audio_queue로 Push

# 🔄 무한 반복 녹음
while True:
    record()
