import os
import redis
import logging

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("result_listener.log"),
        logging.StreamHandler()
    ]
)

# 긍정, 부정 통계
positive_count = 0
positive_score_sum = 0
negative_count = 0
negative_score_sum = 0

result_pubsub = r.pubsub()
result_pubsub.subscribe("result_channel")
logging.info("[Listener] 🎧 Listener started. Waiting for results...")

for message in result_pubsub.listen():
    if message["type"] != "message":
        continue

    try:
        data = message["data"].decode()
        logging.info(f"[Listener] 🎉 STT 결과 수신: {data}")

        # ✔ STT 원본 메시지를 result_messages로 바로 publish (채팅창 출력용)
        r.publish("result_messages", data)

        # ✔ 통계 계산
        if "긍정" in data:
            positive_count += 1
        elif "부정" in data:
            negative_count += 1
        total_count = positive_count + negative_count
        pos_percent = (positive_count / total_count * 100) if total_count else 0
        neg_percent = (negative_count / total_count * 100) if total_count else 0

        # ✔ 통계 메시지 final_stats로 publish (stats 바 영역)
        stats = (
            f"Listener 통계 → 👍{positive_count}회{pos_percent:.0f}%|{neg_percent:.0f}%{negative_count}회 👎"
        )
        logging.info(stats)
        r.publish("final_stats", stats)

    except Exception as e:
        logging.error(f"[Listener] Error: {e}")