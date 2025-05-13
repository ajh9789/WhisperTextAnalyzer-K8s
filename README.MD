# WhisperTextAnalyzer

WhisperTextAnalyzer는 실시간 음성 스트림을 텍스트로 변환하고 감정 분석을 수행하는 End-to-End 파이프라인 시스템입니다.

---

## 📌 프로젝트 개요

- 클라이언트 브라우저에서 **MediaRecorder (Web Audio API 기반)**로 마이크 입력을 캡처하여 FastAPI 서버로 전송
- **FastAPI WebSocket 서버**가 오디오 Blob 데이터를 수신 후 Redis audio_queue에 저장
- **stt_worker (Celery Worker)**가 audio_queue 데이터를 가져와 **OpenAI Whisper 모델**로 STT (Speech-to-Text) 변환
- 텍스트를 Redis text_queue로 전달
- **analyzer_worker (Celery Worker)**가 text_queue의 텍스트를 **transformers 기반 감정 분석 모델**(`distilbert-base-uncased-finetuned-sst-2-english`)로 분석
- 분석 결과는 Redis PubSub의 result_channel로 publish
- **listener 서비스**가 result_channel을 구독하여 결과 및 통계 정보를 파일(`result_listener.log`) + 콘솔에 출력
- 최종적으로 사용자는 Web UI에서 실시간으로 자신의 음성 텍스트 + 감정 분석 결과를 확인 가능

---

## 🛠️ 시스템 아키텍처

## 🛠️ 시스템 아키텍처
````
Client (브라우저: MediaRecorder → WebSocket) //(loacl test는 recorder 서비스)
↓
FastAPI 서비스 (audio_queue로 Redis push)
↓
Redis (audio_queue → text_queue → PubSub result_channel)
↓
stt_worker (Celery + Whisper 모델 → text_queue로 push)
↓
analyzer_worker (Celery + transformers 감정 분석 → result_channel로 publish)
↓
listener (result_channel 구독 → 콘솔 + 파일로 출력)
````



---

## ⚙️ 주요 기술 스택

- FastAPI + WebSocket
- MediaRecorder (Web Audio API 기반)
- Redis (Queue + Pub/Sub)
- Celery (비동기 Worker 관리)
- Whisper (STT 모델, OpenAI Whisper 기반)
- Huggingface Transformers (`distilbert-base-uncased-finetuned-sst-2-english` 감정 분석)
- Docker + Docker Compose
- 
---

## 🧩 개발 중 겪었던 문제 및 해결 방법

### 1. Python whisper vs openai-whisper 혼용 문제
- 초기에는 **패키지 whisper**와 **모듈 whisper(openai-whisper)**가 혼용되어 충돌 발생
- 특히 **Celery worker의 -A 인자에서 worker 파일명과 whisper 패키지명이 충돌** → Celery app load 실패
- **핵심 해결**
  - worker 파일명을 `stt_worker.py`, `analyzer_worker.py` 등으로 명확하게 설정 (절대 whisper.py 쓰지 않음)
  - Celery 실행 시 `celery -A stt_worker:celery_app worker --concurrency=1 --pool=solo`로 정확하게 모듈 지정
- **추가 안전책**
  - 코드에서 import 혼동 방지를 위해 `import whisper as openai_whisper`로 변경

### 2. Windows 환경 개발 시 제한 사항

- Windows + Docker 환경에서 **Celery worker 컨테이너 비정상 종료, crash** 발생
- 원인: **Windows는 fork() 미지원 → spawn() 방식으로 불안정**
- 멀티 concurrency 설정 시 문제 심화 → 반드시 `--pool=solo` 설정 필요  
  → `--pool=solo`: **단일 프로세스, 단일 스레드로만 실행하도록 강제** (Windows 환경에서 안정성 확보)
- Docker에서는 기본적으로 **호스트 마이크 사용 불가**
- 해결:
  - `record` 서비스만 로컬 Python 프로세스로 실행
  - 나머지 서비스(`fastapi_service`, `stt_worker`, `redis`)는 Docker로 운영
  - 또는 Redis만 Docker, 나머지는 로컬로 조합 테스트

#### ✅ Windows vs Linux → Celery 멀티 프로세스 차이

| 시스템 | fork() 지원 | Celery 멀티프로세스 | 결과 |
|-------|-------------|---------------------|------|
| Linux, macOS | ✅ 지원 (`fork()`) | 정상 작동 | 문제 없음 |
| Windows | ❌ 미지원 → `spawn()` | 불안정 | worker crash, hang |

#### ✅ fork() vs spawn() 요약

| 방식 | 특징 | 비유 |
|------|------|------|
| **fork()** | 부모 메모리를 그대로 복제 → 빠르고 안정적 | 복사기로 즉시 복사 |
| **spawn()** | 새 프로세스로 시작 → RAM, CPU 추가 소모 | 새 컴퓨터에 프로그램 재설치 |

#### ✅ Windows에서 spawn()의 문제

- `spawn()`은 새로 Python interpreter + 모든 모듈 + celery context를 다시 로드 → **RAM, CPU 사용량 증가**
- Docker + Celery + Windows 조합에서 child process들이 redis, broker 연결 실패 → **죽음, hang, crash**
- 실질적으로 **Windows에서는 Celery 멀티 프로세스 사용 불가**

### 3. 리눅스 서버 (Azure Linux VM) 배포 시 어려움
- 리눅스는 윈도우와 달라 경로, 파일 권한 등에서 차이가 존재
- 예상치 못한 permission 문제, Redis 접속 문제 발생
- **해결**: Azure VM 환경 맞춰 Docker 재셋팅하고 FastAPI 서버, Redis 서버 따로 튜닝

### 4. STT 서비스의 샘플링 주파수 문제 (실시간 FastAPI 소켓 통신)

Whisper 모델(STT)은 **16,000Hz (16kHz)** 샘플링을 요구합니다.

하지만 브라우저, 모바일, 디바이스 마이크의 기본 샘플링은 보통 **44,100Hz**, **48,000Hz** 등으로 다양하여 **샘플링 불일치 문제**가 발생합니다.

FastAPI WebSocket으로 실시간 스트림 연결 시 서버에서 **Whisper 입력용 PCM 데이터**로 전송해야 합니다.

---

#### ✔ 기존 문제점

기존 **MediaRecorder**, **ScriptProcessorNode** 방식에서는 다음과 같은 문제가 있었습니다.

- AudioContext sampleRate mismatch
- 500ms chunk delay → 실시간성 한계
- Redis로 데이터 전송 시 딜레이 및 누락 문제

---

#### ✔ 최종 개선: AudioWorklet 적용

- **AudioWorklet + AudioContext({ sampleRate: 16000 })**으로 직접 **16kHz 스트림 생성**
- 브라우저에서 실시간 **PCM Float32 buffer** 생성 → **FastAPI WebSocket**으로 즉시 전송
- 서버에서는 별도의 downsampling 없이 바로 **Redis audio_queue**로 push 가능

---

#### ✔ 결과

- 진짜 **low-latency 실시간 스트림 처리** 완성
- 버퍼 크기를 **128~512 frame 수준**으로 조절 가능 → **1020ms 단위 전송** → 거의 통화 수준의 실시간성 확보
- 데이터 손실 및 지연 문제 완벽 해결
- Whisper, Celery stt_worker 구조 변경 없이 그대로 호환

### 5. HTTPS 인증 관련 이슈 (브라우저 마이크 권한)
- 실서버 배포 시 HTTPS가 없으면 브라우저가 마이크 접근 차단
- Let's Encrypt로 무료 SSL 발급 시도했지만, 관리 복잡 + 시간 문제

### 6. ngrok으로 우회 테스트
- 간단히 `ngrok http 8000`을 사용해 HTTPS 우회
- **단점**: ngrok 무료 버전은 1시간마다 주소가 바뀜
- **장점**: 실시간 테스트, 모바일 접속, 다른 PC 접속 등 쉽게 해결 가능

### 7. FastAPI WebSocket 데이터 수신 문제

초기 버전에서는 FastAPI 서버에서 WebSocket으로 들어오는 데이터를 `await websocket.receive()`로 처리했습니다. 이 방식은 FastAPI에서 dict 형태로 데이터를 반환하는데, 브라우저 측에서 binary 데이터를 보낼 경우 데이터가 예상과 다르게 변형되거나 key issue가 발생하는 문제가 있었습니다. 특히 AudioWorklet에서 전송한 PCM Float32 binary buffer가 손실되거나 제대로 전달되지 않는 현상이 발생했습니다.

이에 따라 WebSocket에서 binary 데이터를 안정적으로 수신하려면 `await websocket.receive_bytes()`를 사용하는 것이 표준입니다. 이 방식은 순수 binary 데이터만 직수신할 수 있어 데이터 손실 문제를 해결할 수 있습니다.

| 기존 방식 | 개선 방식 |
|-----------|-----------|
| await websocket.receive() → dict 반환 + 불안정 | await websocket.receive_bytes() → bytes 직수신 |
| 브라우저에서 binary chunk 보낼 때 dict key issue 있음 | binary-only stream이면 receive_bytes로 바로 받는 게 표준 |

특히 AudioWorklet에서 `postMessage(channelData.buffer)` → WebSocket → FastAPI로 전달되는 binary 데이터는 무조건 `receive_bytes()`로 처리해야만 데이터 손실이 발생하지 않습니다.

### 8. Docker multi-container 환경에서 Python module import 불가 문제 및 Celery task trigger로 개선

FastAPI와 stt_worker를 서로 다른 Docker 컨테이너로 분리했을 때, FastAPI에서 `from stt_worker import transcribe_audio` 호출 시 Celery task trigger가 실패했습니다.

#### 원인
- Docker 컨테이너는 서로 파일 시스템을 공유하지 않기 때문에 FastAPI 컨테이너에서는 stt_worker 컨테이너의 모듈을 import할 수 없습니다.
- 초기에는 stt_worker, analyzer_worker 자체 polling 구조 (`while True`로 Redis queue를 반복 확인)로 데이터를 가져가도록 했지만, 컨테이너 분리 이후 FastAPI에서 직접 task 호출이 불가능했습니다.
- 또한 polling 구조는 확장성, 효율성 측면에서 한계가 있었고, Worker가 처리 중일 경우 queue backlog로만 대기하는 구조였습니다.

#### 개선 및 해결
- 현업에서는 컨테이너 간 coupling을 피하기 위해 직접 Python import 대신 Celery의 `send_task()` 메서드를 사용합니다.
- FastAPI는 task 이름 (`"stt_worker.transcribe_audio"`)과 argument (예: bytes 데이터)를 Redis broker로 전달하고, Celery worker가 Redis queue에서 해당 task를 subscribe하여 실행합니다.
- Celery는 내부적으로 모든 Python object (`bytes`, `str`, `dict`, `list` 등)를 직렬화(=바이트화)하여 Redis queue에 저장합니다.  
즉, Worker가 바쁠 경우에도 task는 Redis broker queue에 안전하게 쌓여 대기하게 됩니다.
- 이 방법으로 컨테이너 간 완벽한 독립성을 유지하며, 확장성과 안정성이 향상됩니다.

```python
# ✅ 개선된 실무형 Celery task trigger
# FastAPI → Celery broker (Redis)로 직접 task 전달
# audio_chunk는 bytes 객체 그대로 전달 가능
celery_app.send_task("stt_worker.transcribe_audio", args=[audio_chunk])
```
추가 설명
이전 polling 구조에서는 FastAPI → Redis audio_queue push → Worker가 r.rpop()으로 polling하여 가져갔지만,
개선 구조에서는 send_task()로 직접 Worker에게 전달 → Worker는 바로 인자로 값을 전달받아 처리.
따라서 개선 후에는 Redis audio_queue / text_queue를 사용할 필요가 없으며, r.lpush(), r.rpop() 코드 또한 삭제됩니다.
Celery의 send_task()는 호출 시점에 Redis broker queue에 task를 등록하고,
Worker가 idle 상태가 되면 queue에서 task를 가져와 바로 실행합니다.
Redis broker queue는 실질적인 task buffer 역할을 수행합니다.

### 9. Celery 호출식 직렬화 및 Redis broker 역할 정리

FastAPI → STT worker, STT worker → Analyzer worker 호출 시 Celery의 send_task() 메서드를 사용합니다.

Celery는 task 호출 시 Python object (예: str, list 등)를 자동으로 JSON 직렬화하여 Redis broker에 저장합니다.

Redis는 단순 queue 역할만 하며, 데이터 내용을 변형하거나 해석하지 않습니다.

✅ 핵심 요약  
직렬화(serialize)와 복원(deserialize)은 Celery가 전부 알아서 처리한다.  
Redis는 그저 저장소 역할만 한다.  
Worker 함수 안에서는 Python object (str, list 등)로 이미 복원된 인자를 받는다.

Worker는 Redis에서 task를 가져올 때, Celery가 JSON을 디코드하여 Python object로 복원한 후 task 함수를 호출합니다.

따라서 Worker 함수(analyze_text 등)는 항상 Python native object를 인자로 전달받습니다. (ex. str, list 등)

---

#### ✅ 주요 정리

| 구간 | 역할 | 특징 |
|------|------|------|
| FastAPI → Celery Broker | JSON 직렬화 | Python object → JSON bytes 변환 후 Redis에 저장 |
| Redis Broker | 데이터 저장 | 아무것도 변형하지 않고 저장만 함 |
| Celery Worker → Task | JSON 디코드 | Redis에서 읽은 후 Python object로 복원 |

FastAPI에서 Celery로 넘기는 audio_chunk는 bytes이고,  
STT에서 Analyzer로 넘기는 text는 string입니다.

string은 JSON 직렬화/복원이 자연스럽기 때문에 base64 변환이 필요 없습니다.

결과적으로 analyze_text(text)의 text는 str이기 때문에 .decode()를 호출할 필요가 없습니다.

listener_service처럼 Redis pubsub을 직접 다루는 경우에는 message["data"].decode()를 해줘야 하지만,  
Celery task로 받은 데이터는 이미 복원된 Python object라 decode 없이 그대로 사용해야 합니다.


## 🖼️ 최종 프로젝트 배포 구조
> 개발 중 `record_service`는 테스트용으로 사용했으나, 최종 배포에서는 제외

````
WhisperTextAnalyzer/
├── analyzer_worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py
├── fastapi_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── service.py
├── listener_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── service.py
├── stt_worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── README.md
└── requirements.txt
````


## ✨ 최종 소감
- **Python 환경 (Windows vs Linux)** 차이를 직접 경험하며 배웠음
- 실시간 WebSocket 오디오 스트림 처리의 어려움을 체험
- Whisper 모델이 기대하는 오디오 포맷(WAV, 16kHz, mono)을 맞추는 게 얼마나 까다로운지 이해
- 실서비스 배포까지 직접 다루면서 **Docker, Redis, Celery, Web Audio API** 전체 스택 경험 완료
- ngrok을 통한 간편 테스트 기법을 실무에서 익힘

---

# 📢 주의사항
- 본 프로젝트는 학습 및 데모용이며, 실제 상용 서비스 배포 시 HTTPS/인증/보안 설정이 필수입니다.

````
[User Browser]
 └─ getUserMedia + AudioWorklet (16000Hz PCM buffer)
      ↓
      ↓ WebSocket send (real-time)
[FastAPI Service]
 └── WebSocket → Redis audio_queue에 push

[stt_worker]
 └── Redis audio_queue pop → WAV 변환 → Whisper STT → Redis text_queue

[analyzer_worker]
 └── Redis text_queue pop → Sentiment 분석 → Redis result_channel publish

[listener_service]
 └── Redis result_channel listen → 로그/콘솔 출력
````



