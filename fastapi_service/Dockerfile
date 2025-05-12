# =============================================
# ✅ fastapi_service/Dockerfile (FastAPI용)
# =============================================

FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ✅ 역할: FastAPI WebSocket 서버 컨테이너화
# ✅ Azure 또는 로컬에서 바로 docker-compose로 실행 가능