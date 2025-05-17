FROM python:3.10-slim

WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["celery", "-A", "stt_worker.stt_worker:celery", "worker", "-Q", "stt_queue", "--loglevel=info", "--concurrency=1", "--pool=solo"]