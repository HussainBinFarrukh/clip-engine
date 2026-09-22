FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/apps/api:/app/workers

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/workers

COPY workers/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY workers ./

CMD ["dramatiq", "clip_engine_worker.noop", "clip_engine_worker.jobs"]
