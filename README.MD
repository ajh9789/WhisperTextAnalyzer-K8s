# WhisperTextAnalyzer

WhisperTextAnalyzer는 실시간 음성 스트림을 텍스트로 변환하고 감정 분석을 수행하는 End-to-End 파이프라인 시스템입니다.

---

## 📌 프로젝트 개요

- 브라우저(Web Audio API + AudioWorklet)에서 마이크 입력을 캡처하여 FastAPI 서버로 전송
- FastAPI WebSocket 서버가 오디오 데이터를 Redis broker로 전달
- stt_worker가 OpenAI Whisper로 STT (Speech to Text) 수행
- analyzer_worker가 Huggingface transformers로 감정 분석
- listener_service가 결과를 통계 + 콘솔 + 파일로 출력

---

## 🛠️ 시스템 아키텍처

```
Browser (AudioWorklet) → WebSocket
↓
FastAPI → Redis (Broker)
↓
stt_worker (Whisper STT)
↓
analyzer_worker (Sentiment Analysis)
↓
listener_service (Publish result + stats)
```

참고: 개발 중 recorder_service로 로컬 테스트 가능 (배포에는 미포함)

---

## 📁 폴더 구조

```
WhisperTextAnalyzer/
├── analyzer_worker/
├── fastapi_service/
├── listener_service/
├── recorder_service/ (로컬 테스트용)
├── stt_worker/
├── docker-compose.yml
├── requirements.txt
└── 기타 파일
```

---

## 💻 설치 및 실행 방법

```bash
# Docker 기반 실행
$ docker-compose up --scale stt_worker=2 -d

# Windows: pool=solo 필수 → 이미 적용됨
```

### 📋 주요 컨테이너

- redis : Broker 역할
- stt_worker : Whisper STT (Celery)
- analyzer_worker : Sentiment 분석 (Celery)
- listener_service : 통계 및 결과 출력
- fastapi_service : WebSocket 서버 + 클라이언트 UI

---

## 🧩 주요 문제 및 개선 내역

### 1️⃣ whisper 패키지 충돌 → openai-whisper 명확히 사용

```python
import whisper as openai_whisper
```

### 2️⃣ Windows Docker + Celery crash → pool=solo로 해결

```bash
celery -A stt_worker:celery worker -Q stt_queue --loglevel=info --concurrency=1 --pool=solo
```

### 3️⃣ 브라우저 샘플링 mismatch → AudioWorklet + 16kHz 고정 개선

- AudioContext({ sampleRate: 16000 })
- AudioWorklet → FastAPI로 실시간 binary stream 전송

### 4️⃣ HTTPS 필수 이슈 → ngrok으로 임시 우회 (개발 테스트)

```bash
ngrok http 8000
```

### 5️⃣ FastAPI WebSocket → receive_bytes()로 변경하여 binary 안정 수신

```python
await websocket.receive_bytes()
```

### 6️⃣ Celery send_task()로 컨테이너 간 독립성 확보

```python
celery.send_task("stt_worker.transcribe_audio", args=[audio_chunk], queue="stt_queue")
```

### 7️⃣ Redis default queue 방지 → queue 명시

```bash
celery -A analyzer_worker:celery worker -Q analyzer_queue --loglevel=info
```

### 8️⃣ connection별 buffer 구조로 다중 사용자 안정성 확보

```python
connected_users[websocket] = {"buffer": bytearray(), "start_time": None}
```

### 9️⃣ Silence Threshold 개선 → mobile 대비 0.00001로 ultra low 설정

```javascript
if (energy < 0.00001) return true;
```

### 1️⃣0️⃣ listener 통계 포맷 개선

```python
f"긍정: {positive_count}회 {pos_percent:.0f}% / 부정: {negative_count}회 {neg_percent:.0f}%"
```

### 1️⃣1️⃣ FastAPI on_event() 개선 → redis_subscriber task 안정화

```python
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())
```

### 1️⃣2️⃣ Celery 모델 RAM 중복 문제 → global + if model is None 패턴으로 해결

```python
global model
if model is None:
    model = load_model()
```

---

## 🚀 실 서비스 배포 예시

### nginx + Docker + FastAPI

```
Client (Browser)
↓
nginx → FastAPI (WebSocket + STT)
↓
Redis (Broker)
↓
Celery Worker (STT + Analyzer)
↓
Listener + Dashboard
```

### nginx 설정 예시

```nginx
server {
    listen 80;
    server_name whisperproject.duckdns.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name whisperproject.duckdns.org;
    ssl_certificate /etc/letsencrypt/live/whisperproject.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/whisperproject.duckdns.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

---

## ✅ 최종 개선 버전 핵심 요약

| 개선 항목 | 상태 |
|-----------|------|
| Whisper 모델 STT | ✅ 완성 |
| Sentiment 분석 | ✅ 완성 |
| Listener 통계 | ✅ 개선 완료 |
| FastAPI WebSocket 서버 | ✅ 개선 완료 |
| 실시간 AudioWorklet | ✅ 적용 완료 |
| Multi User Buffer | ✅ 적용 완료 |
| Mobile Threshold 최적화 | ✅ 적용 완료 |

---

## 🎉 최종 소감

- Python + FastAPI + Redis + Celery + Whisper 실서비스 개발 경험
- Docker + Windows/Linux 환경에서의 안정성 개선 학습
- AudioWorklet을 통한 실시간 오디오 스트림 전송 경험
- 실무 시스템 설계 + 최적화 + MSA 기반 구성까지 성공적으로 완수

---

## 📢 주의사항

본 프로젝트는 학습 및 데모용이며, 실제 서비스 배포 시 HTTPS 및 보안 설정을 반드시 강화하세요.