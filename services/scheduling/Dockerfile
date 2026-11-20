# Dockerfile for ClassSync Scheduling Service (Google OR-Tools CP-SAT)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY packages/contracts-py /app/packages/contracts-py
RUN pip install --no-cache-dir /app/packages/contracts-py

COPY services/scheduling/requirements.txt /app/services/scheduling/requirements.txt
RUN pip install --no-cache-dir -r /app/services/scheduling/requirements.txt

COPY services/scheduling /app/services/scheduling

ENV PYTHONPATH="/app"
EXPOSE 8002

CMD ["uvicorn", "services.scheduling.main:app", "--host", "0.0.0.0", "--port", "8002"]
