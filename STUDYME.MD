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

### 10. base64의 이상한 문자 원리와 실무 사용 이유

실무에서 이미지, 오디오, 바이너리 파일 등 **binary data (bytes)**를 network로 안전하게 전달하려면  
**text-only 시스템 (예: JSON, XML, HTTP, WebSocket 등)**을 통과해야 하는 경우가 많습니다.  
하지만 이러한 시스템은 raw bytes를 전달할 수 없어 **깨짐, 오류, 예기치 않은 동작**이 발생합니다.

이를 해결하기 위해 등장한 것이 **base64 인코딩**입니다.

---

#### ✅ base64의 원리

```plaintext
bytes (binary data) → base64 인코딩 → 사람이 읽을 수 있는 ASCII 문자 (str)
```

base64는 **64개의 문자 집합 (A-Z, a-z, 0-9, +, /)**만 사용하여  
어떤 binary data라도 **깨지지 않는 문자열로 변환**합니다.

이 문자열은 사람이 읽으면 의미 없는 알파벳, 숫자, 특수기호 조합으로 보이지만  
**실제론 원본 binary를 완벽하게 복원할 수 있는 문자열 포맷**입니다.

---

#### ✅ 예시 코드

```python
import base64

# 예: 원본 binary 데이터
data = b'\x89PNG\r\n\x1a\n...'  # 이미지나 오디오 파일 등

# base64 인코딩 → str로 변환
b64_string = base64.b64encode(data).decode('utf-8')
print(b64_string)  # → 사람이 보면 이상하지만 JSON-safe 문자열

# base64 디코딩 → 원래 bytes로 복원
restored_data = base64.b64decode(b64_string)
```

출력 예시:
```
iVBORw0KGgoAAAANSUhEUgAA...
```

---

#### ✅ 핵심 요약

| 단계 | 역할 |
|------|------|
| 원본 data | bytes (binary) |
| base64 인코딩 | 이상한 문자로 보이는 ASCII 문자열 (str) |
| 용도 | text-only 시스템에서 binary를 안전하게 전달하기 위해 |

즉, base64 인코딩은  
```
바이트를 이상한 문자(str)로 바꿔서 저장하고 보내는 과정 → YES!
```

실제로 실무에서는 Celery + Redis 또는 Web API에서 image, audio, video를 전달할 때 **필수 표준 방식**으로 사용됩니다.

---


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

### 11. Docker build context + COPY 명령어 동작 원리 + 실무 파일 구조 예시

실무에서 Dockerfile을 작성할 때, `COPY` 명령어는 **Docker build context**를 기준으로 작동합니다.  
Docker build context는 `docker-compose.yml` 또는 `docker build` 명령어에서 지정합니다.

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

---

#### ✅ 원리

1️⃣ `WORKDIR /app` → 이후 모든 작업 경로는 컨테이너 내부 `/app`으로 고정됨  
2️⃣ `COPY requirements.txt .` → build context 기준으로 `requirements.txt`만 복사  
3️⃣ `COPY . .` → build context 내 **모든 파일, 폴더**를 `/app`으로 복사

✅ build context = `./stt_worker`라면 컨테이너 안 `/app` 구조는 다음과 같음:

```plaintext
/app/
├── requirements.txt
├── sst_worker.py
```

(`Dockerfile`은 build용 파일이라 컨테이너로 복사되지 않음)

---

#### ✅ 주의사항

| 상황 | 결과 |
|------|------|
| build context 외부 파일 (`../some_file`) | 복사 불가 |
| 숨김 파일 (`.env`, `.gitignore`, 등) | 포함됨 (단, `.dockerignore`로 제외 가능) |
| COPY . . | build context의 전체 파일 + 폴더 복사 |
| Dockerfile | 포함 안 됨 |

실무에서는 꼭 `.dockerignore` 파일을 만들어 제외할 항목을 설정해야 합니다.

예시:
```plaintext
# .dockerignore 예시
.git
__pycache__
*.pyc
venv
.idea
```

이를 통해 **이미지 용량을 최소화**하고, 불필요한 파일이 포함되지 않도록 할 수 있습니다.

---

#### ✅ 결론

```plaintext
당신 상황에서 build context = ./stt_worker 이므로
컨테이너 /app 안에는 requirements.txt + sst_worker.py 두 파일만 들어간다.
```

실제 실무에서도 이 구조가 **가장 표준적이며 추천되는 방법**입니다.

### 12. openai-whisper 패키지 충돌 문제 및 실무 해결 방법

본 프로젝트 개발 중 가장 큰 장애 중 하나였던 문제입니다.  
처음에 `whisper==1.1.10` 패키지를 설치했더니 아래와 같은 심각한 충돌이 발생했습니다.

```plaintext
import whisper as openai_whisper → AttributeError, ModuleNotFoundError
```

이유:
```
pypi.org 기준, whisper==1.1.10은 openai whisper가 아닌
완전히 다른 Graphite metrics 툴 whisper 패키지였습니다.
(진짜 전세계 Python 개발자들이 낚이는 classic 문제)
```

---

#### ✅ 문제 상황
openai-whisper 패키지 문제
```bash
pip install whisper==1.1.10
```

→ 완전히 엉뚱한 패키지가 설치됨 → openai whisper 모델 사용 불가

→ 해당 문제로 약 하루 이상 디버깅 소요됨

---

#### ✅ 최종 실무 해결 방법

아래와 같이 `openai-whisper` 패키지 최신 버전을 명확하게 설치해야만 했습니다.

최종 requirements.txt 조합:
```plaintext
numpy==1.26.4
scipy==1.13.0
celery==5.3.6
redis==5.0.4
fastapi==0.115.2
uvicorn[standard]==0.29.0
torch==2.2.2+cpu
openai_whisper==20240930
-f https://download.pytorch.org/whl/torch_stable.html
```

핵심 포인트:
- `openai_whisper==20240930` → 진짜 openai whisper 최신 안정 버전
- `torch==2.2.2+cpu` + pytorch wheel source 명시 → 안정적인 CPU 버전 설치
- 실무에서도 가장 안정적인 whisper + pytorch 조합

---

#### ✅ 실무 팁

또는 실무에서는 아래처럼도 많이 설치합니다.
```bash
pip install openai-whisper
```
→ `openai-whisper==2024xxxx` 최신 버전 자동 설치

하지만 연구/배포 환경에서는 항상 명확한 버전 고정을 권장합니다.

---

#### ✅ 발표/문서 주의 포인트

```plaintext
whisper 패키지는 반드시 openai-whisper로 명확하게 지정해야 합니다.
whisper==1.1.10 절대 설치 금지 → 전혀 다른 패키지입니다.
```
## 13.Celery Task에서 전용 큐를 미지정
### 🎯 문제 원인
Docker multi-container 구조에서는 기본적으로 모든 Celery worker가 기본 queue(`"celery"`)를 구독합니다.  
이로 인해 **모든 worker가 모든 task를 수신하려 시도** → 자기 task가 아니면 KeyError가 발생합니다.
### ✅ 해결 원칙
**각 worker는 고유 queue만 구독**하고,  
**FastAPI에서 send_task 시 명확하게 queue를 지정**
````
command: celery -A stt_worker:celery worker -Q stt_queue --loglevel=info
celery.send_task("stt_worker.transcribe_audio", args=[audio_chunk], queue="stt_queue")
@celery.task(name="stt_worker.transcribe_audio")
````
---
## 🐳 Dockerfile 레이어와 캐시 구조 원리

### ✅ Dockerfile 빌드 시 레이어 구조
Docker는 각 명령어마다 레이어를 생성하며, 레이어는 다음과 같이 쌓인다.

FROM python:3.10-slim # Layer 1 (Base Image)
WORKDIR /app # Layer 2
RUN apt-get update &&
apt-get install -y ffmpeg &&
apt-get clean # Layer 3 (System Package Layer)
RUN pip install --upgrade pip # Layer 4 (Python Layer)
COPY requirements.txt . # Layer 5 (File Change Layer)
RUN pip install -r requirements.txt # Layer 6 (Dependency Layer)
COPY . . # Layer 7 (Source Code Layer)


### ✅ 레이어 캐시의 원칙
Docker는 동일한 명령어 + 동일한 파일 + 동일한 context라면 이전 레이어를 캐시에서 재사용한다.

캐시가 유지되는 조건:
- Dockerfile 내용이 변경되지 않았을 때
- Base Image (`FROM`)가 동일할 때
- `COPY`, `ADD` 등으로 복사된 파일 내용이 동일할 때
- Build context (`build: context:` 디렉토리) 파일 변경이 없을 때

캐시가 깨지는 조건:
- Base Image가 변경되었을 때
- Dockerfile 명령어가 변경되었을 때
- requirements.txt 파일이 변경되었을 때 (`COPY requirements.txt .`)
- 소스 코드가 변경되었을 때 (`COPY . .`)
- 시스템 패키지 명령 (`RUN apt-get install ...`)이 추가 또는 변경되었을 때

### ✅ docker-compose의 build context와 캐시
docker-compose의 `build: context:` 설정 자체는 캐시를 깨지 않는다.  
단, 해당 context 내부 파일이 변경되면 캐시가 무효화된다.

- `docker-compose build` → 내부적으로 `docker build -f Dockerfile ./` 와 동일
- stt_worker, analyzer_worker, fastapi_service 등 context가 다르면 캐시는 서로 영향을 주지 않는다.

### ✅ Best Practice
- 시스템 레이어 (`apt-get`) → Python 레이어 (`pip`) → 코드 복사 순으로 작성 권장
- 변경 가능성이 낮은 명령어를 위에 두어 캐시 효율을 극대화

**추천 Dockerfile 예시**
FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

---
# WhisperTextAnalyzer 배포 가이드

이 문서는 **WhisperTextAnalyzer** 애플리케이션을 **nginx, Docker, FastAPI** 환경에서 배포하는 방법을 설명합니다.

## 1. **서버 환경 설정**

### 1.1. **VM에 nginx 설치**
nginx는 FastAPI 애플리케이션에 대한 요청을 프록시하는 역할을 합니다. `nginx`를 설치하려면 아래 명령어를 사용합니다.

```bash
sudo apt update
sudo apt install nginx
설치 후 nginx가 자동으로 실행되며, /etc/nginx/ 경로에서 nginx 설정을 관리할 수 있습니다.

1.2. SSL 인증서 설정 (Let's Encrypt)
웹사이트의 HTTPS 설정을 위해 Certbot을 사용하여 SSL 인증서를 설치합니다.

bash
복사
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d whisperproject.duckdns.org -d www.whisperproject.duckdns.org
이 명령어는 Let's Encrypt로부터 무료 SSL 인증서를 자동으로 받아 nginx 설정에 추가합니다.

2. nginx 설정
nginx 설정 파일은 /etc/nginx/sites-available/default에서 수정할 수 있습니다. 기본 HTTP를 HTTPS로 리디렉션하고, Docker로 실행 중인 FastAPI 애플리케이션으로 요청을 프록시하는 설정을 추가합니다.

nginx
복사
server {
    listen 80;
    server_name whisperproject.duckdns.org www.whisperproject.duckdns.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name whisperproject.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/whisperproject.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/whisperproject.duckdns.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
2.1. 설정 확인 및 nginx 재시작
nginx 설정을 완료한 후, 설정이 올바른지 점검하고 nginx를 재시작합니다.

bash
복사
sudo nginx -t
sudo systemctl restart nginx
3. Docker 환경 설정
3.1. Dockerfile 준비
FastAPI 애플리케이션을 Docker 컨테이너에서 실행하려면 Dockerfile을 준비합니다. 아래는 기본적인 FastAPI Dockerfile 예시입니다.

dockerfile
복사
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["uvicorn", "fastapi_service:app", "--host", "0.0.0.0", "--port", "8000"]
3.2. Docker Compose 사용
docker-compose.yml 파일을 사용하여 FastAPI 컨테이너와 nginx 컨테이너를 동시에 관리할 수 있습니다.

yaml
복사
version: '3'
services:
  app:
    image: fastapi_image
    build:
      context: .
    ports:
      - "8000:8000"
    restart: always  # 컨테이너가 다운되면 자동으로 재시작

  nginx:
    image: nginx:latest
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    restart: always  # nginx도 자동 재시작
3.3. Docker 컨테이너 실행
이제 docker-compose를 사용하여 FastAPI와 nginx 서비스를 시작합니다.

bash
복사
docker-compose up --build -d
4. 테스트
4.1. 브라우저 접속
브라우저에서 https://whisperproject.duckdns.org에 접속하여 FastAPI 서비스가 정상적으로 동작하는지 확인합니다.

4.2. FastAPI 상태 확인
FastAPI가 정상적으로 작동하는지 확인하려면 컨테이너 내부에서 상태를 점검합니다.

bash
복사
curl http://127.0.0.1:8000
정상적으로 FastAPI 애플리케이션의 JSON 응답이 나온다면, 모든 설정이 완료된 것입니다.

5. 자동화 및 유지보수
5.1. 자동 재시작
docker-compose.yml에서 restart: always 옵션을 설정하여, 서버가 재시작되거나 장애가 발생해도 자동으로 복구됩니다.

5.2. Certbot 인증서 자동 갱신
Certbot은 자동으로 인증서를 갱신하지만, 만약 수동으로 갱신하고 싶다면 아래 명령어를 사용합니다.

bash
복사
sudo certbot renew --quiet
이를 cronjob으로 자동화할 수 있습니다.

이 리드미는 nginx + Docker + FastAPI 환경에서 배포하는 데 필요한 모든 단계를 다루고 있습니다.
따라서 WhisperTextAnalyzer 애플리케이션을 정상적으로 배포하고, 인증서를 설정하고, 서비스를 운영할 수 있습니다.

````

# WhisperTextAnalyzer nginx 설정 완성판
````
# HTTP → HTTPS 리디렉션 (필수)
server {
    listen 80;
    listen [::]:80;
    server_name whisperproject.duckdns.org;

    return 301 https://$host$request_uri;
}

# HTTPS + FastAPI + WebSocket 프록시
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name 도메인이름;

    # ➡️ certbot 또는 직접 받은 인증서 경로
    ssl_certificate /인증서 경로/fullchain.pem;
    ssl_certificate_key /인증서 경로/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # -----------------------
    # 일반 HTTP → FastAPI
    # -----------------------
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        client_max_body_size 100M;
        proxy_buffer_size 512k;
        proxy_buffers 4 512k;
        proxy_busy_buffers_size 512k;
        proxy_read_timeout 3600s;
    }

    # -----------------------
    # WebSocket → FastAPI
    # -----------------------
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;

        proxy_buffer_size 512k;
        proxy_buffers 4 512k;
        proxy_busy_buffers_size 512k;
        proxy_read_timeout 3600s;
    }

    # /ws/ path 대응
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;

        proxy_buffer_size 512k;
        proxy_buffers 4 512k;
        proxy_busy_buffers_size 512k;
        proxy_read_timeout 3600s;
    }
}
````



````
## 🖼️ 최종 프로젝트 배포 구조
>✅ 기준: 2024-05-14 최종 프로젝트 구조 기준  
>✅ 이 구조는 Docker + Celery + FastAPI + Redis + Listener + Recorder + Analyzer 서비스 분리 구조입니다.  
>✅ 각 서비스는 독립적인 Dockerfile + requirements.txt를 가집니다.  
>✅ 개발 중 `record_service`는 로컬 테스트용으로 사용했으나, 최종 배포에서는 제외
```plaintext
WhisperTextAnalyzer/
├── analyzer_worker/
│   ├── Dockerfile
│   ├── analyze_worker.py
│   └── requirements.txt
├── fastapi_service/
│   ├── Dockerfile
│   ├── fastapi_service.py
│   └── requirements.txt
├── listener_service/
│   ├── Dockerfile
│   ├── listener_service.py
│   └── requirements.txt
├── recorder_service/
│   ├── Dockerfile
│   ├── recorder_service.py
│   └── requirements.txt
├── stt_worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── sst_worker.py
├── venv/ (가상환경 폴더)
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── README.md
└── requirements.txt (root requirements 파일)
```
---

## ✨ 최종 소감
- 아직 완벽한 MSA는 아니지만, MSA 느낌으로 컨테이너/서비스 분리를 시도했다.
- **Python 환경 (Windows vs Linux)** 차이를 직접 경험하며 배웠음
- 실시간 WebSocket 오디오 스트림 처리의 어려움을 체험
- Whisper 모델이 기대하는 오디오 포맷(WAV, 16kHz, mono)을 맞추는 게 얼마나 까다로운지 이해
- 실서비스 배포까지 직접 다루면서 **Docker, Redis, Celery, Web Audio API** 전체 스택 경험 완료
- ngrok을 통한 간편 테스트 기법을 실무에서 익힘

---

# 📢 주의사항
- 본 프로젝트는 학습 및 데모용이며, 실제 상용 서비스 배포 시 HTTPS/인증/보안 설정이 필수입니다.
