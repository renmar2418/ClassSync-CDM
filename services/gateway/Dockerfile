# Python Microservice Base Dockerfile - ClassSync Gateway
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy packages and requirements
COPY packages/contracts-py /app/packages/contracts-py
RUN pip install --no-cache-dir /app/packages/contracts-py

COPY services/gateway/requirements.txt /app/services/gateway/requirements.txt
RUN pip install --no-cache-dir -r /app/services/gateway/requirements.txt

COPY services/gateway /app/services/gateway

ENV PYTHONPATH="/app"
EXPOSE 8000

CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
