FROM python:3.11-slim

WORKDIR /app

COPY packages/contracts-py /app/packages/contracts-py
RUN pip install --no-cache-dir /app/packages/contracts-py

COPY services/notification/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/notification /app/services/notification

ENV PORT=8003
EXPOSE 8003

CMD ["uvicorn", "services.notification.main:app", "--host", "0.0.0.0", "--port", "8003"]
