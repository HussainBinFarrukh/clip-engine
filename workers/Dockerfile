FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/workers

WORKDIR /app/workers

COPY workers/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY workers ./

CMD ["dramatiq", "clip_engine_worker.noop"]
