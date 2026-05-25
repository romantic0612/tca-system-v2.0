FROM node:22-slim AS vue-builder

WORKDIR /app/frontend/vue-app

COPY frontend/vue-app/package*.json ./
RUN npm ci

COPY frontend/vue-app/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=vue-builder /app/frontend/vue-app/dist /app/frontend/vue-app/dist

RUN mkdir -p /app/data

EXPOSE 5000

CMD ["python", "start.py"]
