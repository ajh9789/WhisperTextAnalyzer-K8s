# Python 3.10 슬림 베이스 이미지
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 시스템 패키지 설치 (ffmpeg 등)
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# pip 최신화 (cu115 같은 local 버전 인식 위함)
RUN pip install --upgrade pip setuptools wheel

# ✅ torch & torchaudio GPU 버전 (CUDA 11.5, Python 3.10) 직접 설치
RUN pip install \
  https://download.pytorch.org/whl/cu115/torch-1.10.0%2Bcu115-cp310-cp310-linux_x86_64.whl \
  https://download.pytorch.org/whl/cu115/torchaudio-0.10.0%2Bcu115-cp310-cp310-linux_x86_64.whl

# requirements_gpu.txt → requirements.txt 이름으로 복사
COPY requirements_gpu.txt ./requirements.txt

# 나머지 라이브러리 설치 (torch 제외)
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 전체 복사
COPY . .

# Celery 워커 실행 (concurrency 제한 포함)
CMD ["celery", "-A", "stt_worker:celery", "worker", "-Q", "stt_queue", "--loglevel=info", "--concurrency=1", "--pool=solo"]
