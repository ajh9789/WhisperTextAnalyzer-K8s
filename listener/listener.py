import redis

# Redis 연결
r = redis.Redis(host="redis", port=6379)
pubsub = r.pubsub()
pubsub.subscribe("result_channel")

# 🎧 실시간 결과 수신 및 출력
print("📢 실시간 감정 분석 결과:")
for message in pubsub.listen():
    if message['type'] == 'message':
        print(message['data'].decode())
