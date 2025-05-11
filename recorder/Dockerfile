# =============================================
# ✅ recorder/Dockerfile
# =============================================

FROM python:3.9
WORKDIR /app
COPY . .
COPY ../requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 서비스 코드 계속 추가 예정
