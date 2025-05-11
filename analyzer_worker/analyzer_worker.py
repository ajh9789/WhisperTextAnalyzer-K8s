# ========================
# 🎙️ Whisper Text Analyzer - Analyzer Worker 서비스
# 🎙️ text_queue → 감정 분석 → result_channel로 전송
# ========================

import os
import redis
from transformers import pipeline
import time

# ========================
# 🎯 Redis 연결 설정
# ========================

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", 0.5))  # polling 간격 (초)

# Redis 클라이언트 생성
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# 감정 분석 모델 (한국어 전용 KoELECTRA 기반)
classifier = pipeline(
    "sentiment-analysis",
    model="monologg/koelectra-small-discriminator"
)

print(f"✅ analyzer_worker 연결 Redis host: {REDIS_HOST}")
print("✅ Sentiment classifier 로드 완료")

# ========================
# 🎯 텍스트 분석 함수
# ========================

def analyze_text():
    """
    text_queue → 감정 분석 → result_channel publish
    """
    try:
        # Redis text_queue에서 텍스트 수신
        text_bytes = r.rpop("text_queue")
        if not text_bytes:
            return  # queue 비어있으면 return

        text = text_bytes.decode("utf-8")

        # 감정 분석 실행
        result = classifier(text)[0]
        emotion = result['label']

        # 결과를 result_channel로 publish
        r.publish("result_channel", f"{text} → {emotion}")
        print(f"✅ [Analyzer 완료] {text} → {emotion}")

    except Exception as e:
        print(f"❌ Analyzer 오류: {e}")

# ========================
# 🎯 메인 루프 (polling 방식)
# ========================

if __name__ == "__main__":
    print("🎯 Analyzer polling 시작")
    while True:
        analyze_text()
        time.sleep(POLL_INTERVAL)  # polling 주기 대기
