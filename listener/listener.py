# =============================================
# ✅ listener/listener.py 최종 발표용 개선 버전
# =============================================

import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost")
REDIS_PORT = 6379

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
pubsub = r.pubsub()
pubsub.subscribe("result_channel")

print("🎧 Listener started. Waiting for results...")

positive_count = 0
positive_score_sum = 0.0
negative_count = 0
negative_score_sum = 0.0

for message in pubsub.listen():
    if message['type'] == 'message':
        data = message['data'].decode()
        print(f"[STT 결과] {data}")

        # 통계 업데이트
        if "긍정" in data:
            positive_count += 1
            try:
                score = float(data.split("[")[1].split("]")[0])
                positive_score_sum += score
            except:
                pass
        elif "부정" in data:
            negative_count += 1
            try:
                score = float(data.split("[")[1].split("]")[0])
                negative_score_sum += score
            except:
                pass

        # 실시간 통계 출력
        print(f"✅ 통계 → 긍정: {positive_count}회, 평균 {positive_score_sum/positive_count if positive_count else 0:.2f} / 부정: {negative_count}회, 평균 {negative_score_sum/negative_count if negative_count else 0:.2f}")
