import os  # 운영체제 환경변수 접근을 위한 모듈
import re  # 정규표현식 처리 모듈
import numpy as np  # 오디오 데이터를 배열로 처리하기 위한 numpy 모듈
from scipy.io.wavfile import write  # numpy 배열을 wav 파일로 저장하기 위한 write 함수
import whisper as openai_whisper  # OpenAI Whisper 모델 불러오기
from celery import Celery  # 비동기 작업 처리를 위한 Celery 모듈
import tempfile  # 임시 파일 생성용 모듈

# from collections import deque

# ✅ 기본 설정
REDIS_HOST = os.getenv(
    "REDIS_HOST", "redis" if os.getenv("DOCKER") else "localhost"
)  # Redis 주소 환경 변수로 설정 (도커 환경 고려)
celery = Celery(
    "stt_worker", broker=f"redis://{REDIS_HOST}:6379/0"
)  # Celery 앱 인스턴스 생성 및 Redis 브로커 설정

# ✅ Whisper 모델 로드
model_size = os.getenv("MODEL_SIZE", "tiny")  # Whisper 모델 사이즈 설정 (tiny, base 등)
model_path = os.getenv("MODEL_PATH", "/app/models")  # 모델 다운로드 저장 경로 지정
os.makedirs(model_path, exist_ok=True)  # 모델 저장 경로가 없을 경우 생성
model = openai_whisper.load_model(
    model_size, download_root=model_path
)  # Whisper 모델 로드 및 다운로드

# # ✅ 메모리 내 4초 누적 버퍼 (deque로 변경) 웹서버에서 받는걸로 결정 다중이용자 고려하기 편함
# buffer = deque()


# ✅ 반복 텍스트 필터 함수
def is_repetitive(text: str) -> bool:  # 반복 텍스트 필터 함수 정의
    # 공백 제거 후 문자 반복 (예: 아아아아아)
    if re.fullmatch(
        r"(.)\1{4,}", text.replace(" ", "")
    ):  # 같은 문자가 5번 이상 반복되는 경우 (예: 아아아아아)
        return True
    # 단어 반복 (예: 좋아요 좋아요 좋아요 좋아요 좋아요)
    if re.search(
        r"\b(\w+)\b(?: \1){4,}", text
    ):  # 같은 단어가 5번 이상 반복되는 경우 (예: 좋아요 좋아요 ...)
        return True
    # 음절 반복 (예: 아 아 아 아 아)
    if re.fullmatch(
        r"(.)\s*(?:\1\s*){4,}", text
    ):  # 음절 단위로 반복되는 경우 (예: 아 아 아 아 아)
        return True
    return False


@celery.task(
    name="stt_worker.transcribe_audio", queue="stt_queue"
)  # Celery 태스크 등록: STT 작업 함수
def transcribe_audio(audio_bytes):  # STT 오디오 처리 함수 정의
    print("[STT] 🎧 오디오 청크 수신")
    audio_np = np.frombuffer(
        audio_bytes, dtype=np.int16
    )  # 'bytes' 데이터를 numpy int16 배열로 변환
    with tempfile.NamedTemporaryFile(
        suffix=".wav"
    ) as tmpfile:  # 오디오 데이터를 임시 WAV 파일로 저장
        write(
            tmpfile.name, 16000, audio_np.astype(np.int16)
        )  # numpy 배열을 16kHz wav로 저장
        try:
            result = model.transcribe(
                tmpfile.name, language="ko", fp16=False
            )  # Whisper 모델로 음성 인식 수행
            text = result.get(
                "text", ""
            ).strip()  # 결과에서 앞뒤 텍스트 추출 및 공백 제거

            if not text:  # 공백 결과일 경우 분석 생략
                print("[STT] ⚠️ 공백 텍스트 → 분석 생략")
                return

            if is_repetitive(text):  # 반복 텍스트 필터링 적용
                print(f"[STT] ⚠️ 반복 텍스트 감지 → 분석 생략: {text}")
                return

            print(f"[STT] 🎙️ Whisper STT 결과: {text}")

        except Exception as e:
            print(f"[STT] ❌ Whisper 처리 실패: {e}")
            return

        try:
            celery.send_task(  # 분석 결과를 analyzer_worker에게 전달
                "analyzer_worker.analyzer_text", args=[text], queue="analyzer_queue"
            )
            print("[STT] ✅ analyzer_worker 호출 완료")
        except Exception as e:
            print(f"[STT] ❌ analyzer_worker 호출 실패: {e}")
