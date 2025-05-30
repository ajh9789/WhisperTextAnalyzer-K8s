FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && apt-get clean
RUN pip install --upgrade pip

# ✅ torch & torchaudio 먼저 별도 설치 (cu115 인덱스 명시)
RUN pip install torch==1.10.0+cu115 torchaudio==0.10.0+cu115 \
  --extra-index-url https://download.pytorch.org/whl/cu115

# ✅ 그다음 나머지 requirements
COPY requirements_gpu.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["celery", "-A", "stt_worker:celery", "worker", "-Q", "stt_queue", "--loglevel=info"]