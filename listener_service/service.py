import os
import redis
import logging

# ✅ logging 설정 (파일 + 콘솔)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("result_listener.log"),   # 🔥 파일로 저장
        logging.StreamHandler()                       # 🔥 콘솔에도 출력
    ]
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
pubsub = r.pubsub()
pubsub.subscribe("result_channel")

logging.info("🎧 Listener started. Waiting for results...")

positive_count = 0
positive_score_sum = 0.0
negative_count = 0
negative_score_sum = 0.0

for message in pubsub.listen():
    if message["type"] == "message":
        try:
            data = message["data"].decode()
        except Exception as e:
            logging.error(f"[Listener] Decode error: {e}")
            continue

        logging.info(f"[STT 결과] {data}")

        # ✅ 통계 업데이트
        try:
            if "긍정" in data:
                positive_count += 1
                score = float(data.split("[")[1].split("]")[0])
                positive_score_sum += score
            elif "부정" in data:
                negative_count += 1
                score = float(data.split("[")[1].split("]")[0])
                negative_score_sum += score
        except Exception as e:
            logging.error(f"[Listener] Score parse error: {e}")

        # ✅ 실시간 통계 출력 + 로그 저장
        stats = (
            f"✅ 통계 → 긍정: {positive_count}회, 평균 {positive_score_sum/positive_count if positive_count else 0:.2f} / "
            f"부정: {negative_count}회, 평균 {negative_score_sum/negative_count if negative_count else 0:.2f}"
        )
        logging.info(stats)
