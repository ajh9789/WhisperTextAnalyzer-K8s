# =============================================
# ✅ listener/listener.py 개선 최종 버전
# =============================================
import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
pubsub = r.pubsub()
pubsub.subscribe("result_channel")

print("🎧 Listener started. Waiting for results...")
for message in pubsub.listen():
    if message['type'] == 'message':
        print(f"[STT 결과] {message['data'].decode()}")
