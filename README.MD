# WhisperTextAnalyzer

WhisperTextAnalyzer는 실시간 음성 스트림을 텍스트로 변환하고 감정 분석을 수행하는 End-to-End 파이프라인 시스템입니다.
<p>
  <img src="https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Redis-Broker-DC382D?logo=redis&logoColor=white"/>
  <img src="https://img.shields.io/badge/Celery-Task%20Queue-37814A?logo=celery&logoColor=white"/>
  <img src="https://img.shields.io/badge/OpenAI-Whisper-3D3D3D?logo=openai&logoColor=white"/>
  <img src="https://img.shields.io/badge/HuggingFace-Transformers-FFD21F?logo=huggingface&logoColor=black"/>
  <img src="https://img.shields.io/badge/sounddevice-Audio-blueviolet"/>
  <img src="https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/Azure-Cloud%20Server-0078D4?logo=microsoftazure&logoColor=white"/>
  <img src="https://img.shields.io/badge/Linux-Server-FCC624?logo=linux&logoColor=black"/>
  <img src="https://img.shields.io/badge/Nginx-Reverse%20Proxy-009639?logo=nginx&logoColor=white"/>
  <img src="https://img.shields.io/badge/NVIDIA-RTX%203070-76B900?logo=nvidia&logoColor=white"/>
  <img src="https://img.shields.io/badge/Windows-10%2B-0078D6?logo=windows&logoColor=white"/>
  <img src="https://img.shields.io/badge/ChatGPT-Assistant-10a37f?logo=openai&logoColor=white"/>
  <img src="https://img.shields.io/badge/PyCharm-Professional-000000?logo=jetbrains&logoColor=white"/>
  <img src="https://img.shields.io/badge/Git-Version%20Control-F05032?logo=git&logoColor=white"/>
</p>

## 📸 WhisperTextAnalyzer 시스템 실행 예시

<p>
  <img src="img.jpg" alt="WhisperTextAnalyzer 시스템 실행 예시" width="50%"/>
</p>
---

## 🎉 최종 소감

---
- Python + FastAPI + Redis + Celery 기반의 STT와 감정 분석 기능으로 배포까지 개발 경험
- Celery (비동기 task queue, worker 분산 처리 개념 학습)와 Redis (queue + pub/sub message broker 역할)를 실무 수준으로 이해
- Docker 이해를 높일 수 있는 (컨테이너 기반 분산 시스템 구축, Windows + Linux 환경 차이, 이미지 최적화) 실습 경험
- 실무 시스템 설계에 가깝게 하기 위해 최적화와 MSA (microservice architecture) 기반 유사한 구성까지 성공적으로 완수
- WebSocket 소켓 통신 및 AudioWorklet을 통한 실시간 오디오 스트림 전송 기술 학습 및 구현
---

---
## 📌 프로젝트 개요
- 브라우저(Web Audio API + AudioWorklet)에서 마이크 입력을 캡처하여 FastAPI 서버로 전송
- FastAPI WebSocket 서버가 오디오 데이터를 Redis Broker(stt_queue)로 전달
- stt_worker가 OpenAI Whisper로 STT (Speech to Text) 수행 후 Redis Queue(analyzer_queue)에 결과 전달
- analyzer_worker가 Huggingface Transformers로 감정 분석 수행
- listener_service가 Redis Pub/Sub(result_channel, final_stats)을 통해 결과 및 통계 데이터를 발행
- FastAPI가 Redis Pub/Sub 구독 → 클라이언트로 WebSocket 실시간 결과 업데이트

---

## 🛠️ 시스템 아키텍처

```
Browser (AudioWorklet) 
        ↓
    WebSocket
        ↓
FastAPI → Redis Queue (stt_queue)
        ↓
    stt_worker (Whisper STT)
        ↓
    Redis Queue (analyzer_queue)
        ↓
analyzer_worker (Sentiment Analysis)
        ↓
    Redis Pub/Sub (result_channel, final_stats)
        ↓
listener_service (Publish result + stats → Redis Pub/Sub)
        ↓
    FastAPI (Redis Subscriber → WebSocket push)
        ↓
Browser 실시간 결과 업데이트
```

참고: 개발 중 recorder_service로 로컬 테스트 (배포에는 미포함)

---
## 🚀 실 서비스 배포 경험

WhisperTextAnalyzer 프로젝트는 개발 → 테스트 → 실배포까지 모든 과정을 직접 수행했습니다.

### 🛠️ 배포 과정
- Azure Linux VM 실서버 구축
- 개발 단계에서 ngrok로 HTTPS 개발 테스트
- 무료 도메인 서비스 [DuckDNS](https://www.duckdns.org) 사용
- Let's Encrypt로 SSL 인증서 발급 및 적용
- nginx + Docker + FastAPI 연동하여 MSA 구조 구성
- Celery Worker + Redis Broker + WebSocket 실시간 연동

### 🌐 실 서비스 주소(현재는 막힘!)
[https://whisperproject.duckdns.org/](https://whisperproject.duckdns.org/)
```
---

## 📁 폴더 구조

```
WhisperTextAnalyzer/
├── analyzer_worker/ # 감정 분석 Celery Worker (Huggingface Transformers)
│ ├── Dockerfile
│ ├── analyzer_worker.py
│ └── 기타 설정 파일
│
├── fastapi_service/ # FastAPI WebSocket Server + 클라이언트 UI + Redis Subscriber
│ ├── Dockerfile
│ ├── fastapi_service.py
│ └── 기타 설정 파일
│
├── listener_service/ # Redis Pub/Sub Listener → result_channel, final_stats 처리
│ ├── Dockerfile
│ ├── listener_service.py
│ └── 기타 설정 파일
│
├── recorder_service/ # 🎙️ (로컬 테스트용) 마이크 입력 → Redis push
│ ├── recorder_service.py
│ └── 기타 설정 파일
│
├── stt_worker/ # Whisper 기반 STT Celery Worker
│ ├── Dockerfile
│ ├── stt_worker.py
│ └── 기타 설정 파일
│
├── docker-compose.yml # 전체 컨테이너 오케스트레이션
├── requirements.txt # Python 패키지 의존성 정의
├── README.md # 프로젝트 문서
└── 기타 파일 # .env, .gitignore 등 기타 설정 파일
```

---

## 💻 설치 및 실행 방법

모든 서비스는 Docker Compose 기반으로 실행됩니다.  
아래 명령어를 순서대로 입력하세요.

```bash
# 1. 도커 이미지 빌드
docker-compose build

# 2. 컨테이너 실행 (stt_worker는 2개로 스케일링)
docker-compose up --scale stt_worker=2 -d
```

```bash
💡 참고: 현재 compose에는 윈도용 --concurrency=1 --pool=solo 옵션이 이미 적용되어 있습니다.
윈도우에서 사용시 stt_worker을 복사해서 stt_worker1로 사용하시면 됩니다.
```
---
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

## 📢 주의사항

본 프로젝트는 학습 및 데모용이며, 실제 서비스 배포 시 HTTPS 및 보안 설정을 반드시 강화하세요.
