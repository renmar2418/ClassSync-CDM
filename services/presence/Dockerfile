# Dockerfile for ClassSync Presence Service (TOTP QR & Workstations)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/contracts-py /app/packages/contracts-py
RUN pip install --no-cache-dir /app/packages/contracts-py

COPY services/presence/requirements.txt /app/services/presence/requirements.txt
RUN pip install --no-cache-dir -r /app/services/presence/requirements.txt

COPY services/presence /app/services/presence

ENV PYTHONPATH="/app"
EXPOSE 8004

CMD ["uvicorn", "services.presence.main:app", "--host", "0.0.0.0", "--port", "8004"]
