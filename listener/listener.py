# ==============================
# ✅ result_listener.py : redis pubsub → 결과 출력
# ==============================

import redis
import os

r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379)
pubsub = r.pubsub()
pubsub.subscribe("result_channel")

print("📢 실시간 감정 분석 결과:")
for message in pubsub.listen():
    if message['type'] == 'message':
        print(message['data'].decode())