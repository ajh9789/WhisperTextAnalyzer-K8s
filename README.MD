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

# 🎧 WhisperTextAnalyzer

> **실시간 음성 스트리밍 → STT → 감정 분석까지**  
> End-to-End 파이프라인을 구현한 웹 기반 음성 인식 시스템

---
🎯 본 프로젝트는 실무에 가까운 **MSA + 비동기 Task Queue 구조**를 직접 설계하고 **Docker 기반으로 배포**한 예제입니다.  
- 🎙️ **브라우저 AudioWorklet → FastAPI WebSocket → Redis/Celery Task Queue → STT/감정 분석**  
- 실제 서비스 흐름을 유사하게 구성하여, **실시간 음성 → 텍스트 → 감정 분석**까지 자동 처리하며  
- **Azure Linux 서버 + nginx + DuckDNS + HTTPS 인증서**까지 포함한 **실제 배포 경험**까지 수행하였습니다.
---
## 📸 WhisperTextAnalyzer 시스템 실행 예시

<p>
  <img src="img.jpg" alt="WhisperTextAnalyzer 시스템 실행 예시" width="50%"/>
</p>

## 🎉 최종 소감

---
- Python + FastAPI + Redis + Celery 기반의 STT 및 감정 분석 파이프라인을 직접 설계하고, **개발부터 Docker 배포까지 전 과정을 혼자 구현**
- Celery(비동기 Task Queue)와 Redis(Queue 및 Pub/Sub 메시지 브로커)를 활용하여 MSA(Microservice Architecture) 스타일의 구조를 구성하고, 실무에 가까운 처리 흐름과 동작 원리를 체계적으로 학습
- Docker를 기반으로 Windows/Linux 간 환경 차이, 이미지 최적화, 컨테이너 간 통신 구성 등 실무와 유사한 인프라 구축 경험
- 실제 서비스 구조를 고려해 모듈 간 역할 분리, 비동기 병렬 처리, 메시지 큐 흐름 등을 포함한 MSA 유사 아키텍처를 구현
- WebSocket 기반 실시간 통신과 Web Audio API의 AudioWorklet을 활용해, 브라우저에서 실시간 마이크 오디오 스트림을 수집하고 Whisper 모델과 연동
- AudioWorklet 내에 VAD(Vocal Activity Detection) 필터를 적용하여 무음 구간을 제거함으로써, 네트워크 부하와 STT 비용을 효율적으로 절감
---
## 📌 프로젝트 개요
- 브라우저(Web Audio API + AudioWorklet)에서 마이크 입력을 캡처하여 FastAPI 서버로 전송
- FastAPI WebSocket 서버가 수신한 오디오 데이터를 STT 작업용 Celery Task(transcribe_audio)로 비동기 호출 → stt_queue 등록
- stt_worker가 OpenAI Whisper로 음성 인식(STT) 수행 후, Celery Task(analyze_text)를 비동기 호출 → analyzer_queue 등록
- analyzer_worker가 Huggingface Transformers로 감정 분석 수행 후 Redis의 result_channel에 결과 메시지 발행
- listener_service가 result_channel을 구독하여 결과 및 통계를 처리한 뒤, result_messages / final_stats 채널로 각각 발행
- FastAPI가 두 채널을 구독하여, WebSocket을 통해 브라우저에 실시간 결과와 통계를 업데이트
---

## 🛠️ 시스템 아키텍처

```
Browser (AudioWorklet: 마이크 입력 + 16kHz PCM 변환)
        ↓
    WebSocket 전송
        ↓
FastAPI 서버
        ↓
Celery Task (transcribe_audio) 호출 → stt_queue 등록
        ↓
stt_worker (OpenAI Whisper로 STT 수행)
        ↓
Celery Task (analyze_text) 호출 → analyzer_queue 등록
        ↓
analyzer_worker (Huggingface Transformers로 감정 분석)
        ↓
Redis Pub/Sub (result_channel로 결과 발행)
        ↓
listener_service (result_channel 구독 → 통계 처리 → result_messages, final_stats 발행)
        ↓
FastAPI (2개 채널 구독)
        ↓
    WebSocket 전송
        ↓
Browser 실시간 결과 표시
```

참고: 개발 중 recorder_service로 로컬 테스트 (배포에는 미포함)

---

### 📋 주요 컨테이너

- redis : Broker 역할
- stt_worker : 음성 인식 STT 처리 (Celery) OpenAI가 개발한 Whisper는16kHz mono PCM 음성을 받아 텍스트로 출력합니다.
- analyzer_worker : 감정 분석 처리 (Celery)
- listener_service : 결과 및 통계 출력
- fastapi_service : WebSocket 서버 + 클라이언트 UI
---
## ✅ 기술 개선 요약 및 구조 안정화 현황

| 개선 항목                                             | 상태 |
|---------------------------------------------------|------|
| Whisper 모델 STT 파이프라인                              | ✅ 완성 |
| Sentiment 분석 모듈                                   | ✅ 완성 |
| Listener 통계 처리                                    | ✅ 개선 완료 |
| FastAPI WebSocket 서버                              | ✅ 개선 완료 |
| 실시간 AudioWorklet + VAD 필터링                        | ✅ 적용 완료 |
| Multi User Buffer 구조                              | ✅ 적용 완료 |
| Silence Threshold 개선                              | ✅ 적용 완료 |
| Whisper 입력 포맷(PCM → WAV 변환)                         | ✅ 구현 완료 |
| WebSocket Binary 안정 수신 처리                         | ✅ 적용 완료 |
| Celery 컨테이너 간 독립성 확보                              | ✅ 적용 완료 |
| Redis Pub/Sub 다채널 구조 설계                           | ✅ 설계 반영 |
| HTTPS/도메인 우회 테스트(ngrok)                           | ✅ 실습 완료 |
| Azure VM + DuckDNS + SSL 인증서 + nginx + Docker 실서버 운영| ✅ 실배포 완료 |
---
## 🧩 주요 문제 및 개선, 학습 내역 1️⃣6️⃣개

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

### 9️⃣ Silence Threshold 개선 → 에너지 기준을 0.0005로 조정하여 음성 인식 민감도 개선

```javascript
if (energy < 0.0005) return true;
```

### 1️⃣0️⃣ FastAPI 서버 시작 시 Redis Subscriber 비동기 등록 구조로 개선

```python
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_subscriber())
```
### 1️⃣1️⃣ WebSocket 통신 구조 학습 → 연결 유지 방식 및 WebSocket 특성 학습  

WebSocket은 HTTP와 달리 지속적인 양방향 연결을 유지하며,  
FastAPI 내부에서 .send_text() 또는 .send_bytes()를 통해 실시간 푸시가 가능함.  
클라이언트가 명시적으로 연결을 닫거나 네트워크 오류가 발생하지 않는 이상 연결은 계속 유지됨.  
→ 오디오 버퍼를 1초마다 전송해도 연결을 새로 여는 구조는 아님
---
### 1️⃣2️⃣ AudioWorklet 동작 원리 및 128프레임 처리 주기 학습  

AudioWorkletProcessor는 약 128 샘플 단위 / 8ms 간격으로 process() 호출됨 (sampleRate: 16000 기준)  
내부에서 Float32 → Int16 변환 후, port.postMessage()를 통해 FastAPI로 전달  
WebSocket 전송 시 자동으로 ArrayBuffer → 바이너리 스트림으로 직렬화됨 → 서버에서는 receive_bytes()로 수신  
각 프레임의 에너지를 계산하여 VAD 필터링을 적용함 (energy < 0.0005 시 무음으로 판단)  
---
### 1️⃣3️⃣ PCM vs WAV 차이 학습 → Whisper 입력 구조 학습  

PCM은 디지털 오디오의 원본(raw) 데이터이고, WAV는 여기에 헤더를 붙인 파일 포맷  
Whisper는 16kHz, mono 채널, int16 PCM 포맷을 요구함  
따라서 scipy.io.wavfile.write()를 통해 .wav 파일로 저장 후 Whisper 입력에 사용  
---
### 1️⃣4️⃣ Redis Pub/Sub 구조 학습 → 다중 채널 구독 및 재발행 처리 학습  

listener_service는 result_channel을 구독하여 STT 결과 수신  
결과 메시지는 result_messages, 통계 메시지는 final_stats 채널로 각각 재발행  
FastAPI는 두 채널을 asyncio.create_task()로 구독하여, WebSocket을 통해 브라우저에 실시간 전송 
---
### 1️⃣5️⃣ ️오디오 입력 포맷 이해 및 Float32 → Int16 변환 이유 학습  

🎤 마이크 입력 기본 포맷 비교  

| 플랫폼 | 오디오 캡처 방식 | 기본 포맷 | 비고 |
|--------|------------------|------------|------|
| **브라우저 (Chrome, Firefox 등)** | `getUserMedia()` + Web Audio API | `Float32` (32bit 실수형) | Web Audio API는 항상 Float32로 동작 |
| **모바일 (Android, iOS)** | OS별 오디오 SDK | `Int16` PCM | 하드웨어에 따라 다르지만 대부분 16bit PCM |
| **데스크탑 (Windows, Linux 등)** | WASAPI, ALSA, PortAudio 등 | `Int16` 또는 `Float32` | 설정 가능, 기본은 Int16인 경우 많음 |

> 즉, **브라우저 기반 입력은 항상 `Float32`**, Whisper 등 STT 모델은 **`Int16 PCM`**을 요구  

🔁 Float32 vs Int16 비교

| 항목 | `Float32` | `Int16` |
|------|-----------|---------|
| **데이터 형식** | 부동소수점 실수형 | 정수형 |
| **비트 수 / 용량** | 32비트 (4바이트) | 16비트 (2바이트) |
| **값의 범위** | -1.0 ~ +1.0 | -32,768 ~ +32,767 |
| **정밀도** | 소수점 표현 가능 | 정수만 표현 |
| **Web Audio API 기본 포맷** | ✅ 기본 출력 | ❌ 직접 지원 안 함 |
| **STT 모델 입력 지원 (Whisper 등)** | ❌ 지원 안 함 | ✅ 기본 요구 포맷 |
| **전송 효율** | 낮음 (용량 큼) | 높음 (절반 크기) |

❓ 왜 Float32 → Int16 변환이 필요한가?
- Whisper, DeepSpeech 등 대부분의 STT 모델은 **Int16 PCM 입력만 지원**
- 브라우저는 기본적으로 `Float32`로 마이크 입력을 처리하므로,
- **모델 호환성과 전송 효율**을 위해 반드시 **Float32 → Int16 변환**이 필요  

### ✅ 결론
> 변환은 브라우저 내 AudioWorklet에서 수행하거나, 서버에서 후처리 가능  
> 하지만 **클라이언트 측에서 미리 Int16으로 변환하면** 서버 부하와 네트워크 사용량을 줄일 수 있음
---
### 1️⃣6️⃣ Redis + Celery 구조 및 Task Queue 개념 정리
### ❓  Redis는 어떤 역할?  
Redis는 **인메모리 기반의 Key-Value 저장소**이자, 
Redis는 Celery에서 **메시지 브로커(Broker)** 로 사용됩니다.  
즉, FastAPI → Celery Task 요청 시, 작업 내용이 **Redis Queue로 전달되고**,  
**Worker는 해당 Queue를 모니터링하면서 작업을 꺼내 실행**합니다.

✅ Redis의 인메모리 특징

| 항목             | 설명 |
|------------------|------|
| 🔄 **빠른 처리 속도** | 디스크 I/O 없이 메모리에서 직접 읽고 쓰므로 **지연시간이 매우 낮음 (sub-millisecond)** |
| 📦 **데이터 휘발성** | 기본적으로 메모리에만 저장되므로 **서버 재시작 시 데이터 소실 가능**<br>(옵션으로 RDB or AOF 지속성 설정 가능) |
| 💬 **브로커/캐시/세션** | 메시지 브로커 외에도 **캐시, 세션 저장소, Pub/Sub 등 다용도** 활용 가능 |

🔄 Redis 메시지 처리 방식 비교: Queue vs Pub/Sub

| 항목 | Redis List (Queue 방식) | Redis Pub/Sub (채널 발행/구독 방식) |
|------|--------------------------|-------------------------------------|
| 구조 | 작업을 큐에 쌓고 꺼내는 구조 (`lpush` / `blpop`) | 실시간 알림 전송 구조 (`publish` / `subscribe`) |
| 목적 | 비동기 작업 처리 / 안정성 중심 | 실시간 브로드캐스트 중심 |
| 생산자 | `lpush("queue", data)` | `publish("channel", data)` |
| 소비자 | `blpop("queue")` – 큐에서 꺼내 작업 실행 | `subscribe("channel")` – 실시간 수신 |
| 메시지 손실 | ❌ 소비자가 없어도 메시지 보존됨 | ⚠️ 구독자 없으면 메시지 유실됨 |
| 순서 보장 | ✅ FIFO 보장 | ❌ 보장 안됨 |
| 실무 사용 | 비동기 작업 큐, 처리 지연 허용 가능 | 알림, 채팅, 통계 알림 등 실시간 요구에 적합 |
| WhisperTextAnalyzer 내 사용 | STT/감정 분석 요청 큐 (stt_queue / analyzer_queue) | STT 결과 및 통계 전송 (result_channel 등) |

> ✅ 본 프로젝트에서는:
> - **작업 분산 및 안정성 필요 작업**은 `Celery + Redis Queue` 기반으로 처리
> - **브라우저 실시간 알림**은 `Redis Pub/Sub` 방식으로 전달

### ❓ Celery는 어떤 역할?
Celery는 Python 기반의 **비동기 작업 처리 프레임워크**입니다.  
지정한 Task를 **Worker가 백그라운드에서 실행**하도록 분리할 수 있어,  
API 서버와 무거운 작업을 **비동기/비차단 방식으로 분리**하는 데 효과적입니다.

✅ Celery Task 분리로 얻는 이점

| 항목                   | 효과                                                                 |
|----------------------|----------------------------------------------------------------------|
| API와 무거운 처리 분리   | FastAPI는 응답만 처리하고, STT/감정 분석은 Worker가 백그라운드에서 처리                        |
| 장애 격리              | 하나의 Worker 오류 발생 시 → 전체 서버 영향 없이 개별 장애만 발생 (서비스 안정성 향상)          |
| 확장성                 | 작업 종류(stt / analyzer 등)별로 Worker를 나누거나, Worker를 다중 실행하여 수평 확장 가능     |
| 재시도 / 타임아웃 설정    | Celery Task에 retry, acks_late, time_limit 옵션 등을 추가해 작업 실패에 유연하게 대응 가능     |
🛠️ 기본 Celery Task 호출 흐름  

```
FastAPI (Celery send_task) ⬅ queue="stt_queue" 등 지정
↓ 
Redis (Broker / Queue)
↓
stt_worker (Celery Worker가 Queue 모니터링 → 작업 실행)
```
1. Celery 등록 예시

```python
@celery.task(name="stt_worker.transcribe_audio", queue="stt_queue")
def transcribe_audio(audio_bytes):
    ...
```
2. Celery Task 사용 예시
```python
celery.send_task(
    "stt_worker.transcribe_audio",  # 등록된 Task 이름
    args=[audio_bytes],             # 넘겨줄 인자 (음성 바이너리)
    queue="stt_queue"               # 처리할 Celery Queue 지정
)
# args: 작업에 넘길 인자
# queue: 작업이 들어갈 Redis 큐 이름 (컨테이너도 동일 큐를 명시해야함)
```
3. docker-compose 선언 예시
```
services:
  stt_worker:
    build: ./stt_worker
    command: celery -A stt_worker:celery worker -Q stt_queue --loglevel=info --concurrency=1 --pool=solo
    environment:
      - REDIS_HOST=redis
# -Q stt_queue 로 해당 Worker가 처리할 큐를 명시
# --concurrency=1, --pool=solo → 윈도우 환경에서 안정 실행 필수 옵션
```
❓ 왜 큐 이름을 명시해야 하나요?  
>Celery 기본 Queue 이름은 celery 여러 Worker/서비스가 존재할 경우,  
명시하지 않으면 충돌 가능, 혹은 default Redis queue에 들어감  
따라서 반드시 -Q 큐이름 및 queue="큐이름" 을 서버와 워커 양쪽에 명확히 지정해야 안정성 확보

---

## 🚀 실 서비스 배포 경험

WhisperTextAnalyzer 프로젝트는 개발 → 테스트 → 실배포까지 모든 과정을 직접 수행했습니다.

### 🛠️ 배포 과정
- Azure Linux VM 실서버 구축
- 개발 단계에서 ngrok로 HTTPS 개발 테스트
- 무료 도메인 서비스 [DuckDNS](https://www.duckdns.org) 사용
- Let's Encrypt로 SSL 인증서 발급 및 적용
- nginx + Docker + FastAPI 연동하여 구성
- Celery Worker + Redis Broker + WebSocket 실시간 연동

### 🌐 실 서비스 주소(현재는 막힘!)
[https://whisperproject.duckdns.org/](https://whisperproject.duckdns.org/)
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
## 📁 폴더 구조

```
WhisperTextAnalyzer/
├── analyzer_worker/ # 감정 분석 Celery Worker (Huggingface Transformers)
│ ├── Dockerfile
│ ├── analyzer_worker.py
│ └── requirements.txt
│
├── fastapi_service/ # FastAPI WebSocket Server + 클라이언트 UI + Redis Subscriber
│ ├── Dockerfile
│ ├── fastapi_service.py
│ └── requirements.txt
│
├── listener_service/ # Redis Pub/Sub Listener → result_channel, final_stats 처리
│ ├── Dockerfile
│ ├── listener_service.py
│ └── requirements.txt
│
├── recorder_service/ # 🎙️ (로컬 테스트용) 마이크 입력 → Redis push
│ ├── Dockerfile
│ ├── recorder_service.py
│ └── requirements.txt
│
├── stt_worker/ # Whisper 기반 STT Celery Worker
│ ├── Dockerfile
│ ├── stt_worker.py
│ └── requirements.txt
│
├── docker-compose.yml # 도커 컴포즈
├── requirements.txt # Python 패키지 의존성 정의 모음
├── README.md # 프로젝트 문서
└── 기타 파일 # .env, .gitignore 등 기타 설정 파일
```
---

## ⚠️ 주의사항 및 보안 권고
본 프로젝트는 학습 및 데모용이며, 실제 서비스 배포 시 HTTPS 및 보안 설정을 반드시 강화하세요.
