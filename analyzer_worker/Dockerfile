# =============================================
# ✅ analyzer_worker/Dockerfile
# =============================================

FROM python:3.9
WORKDIR /app
COPY . .
COPY ../requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
