FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY livecsv ./livecsv

RUN mkdir -p /data/csv

ENV SG_LIVECSV_DATA_DIR=/data \
    SG_OUTPUT_DIR=/data/csv \
    PORT=8080

VOLUME ["/data"]
EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "main:app"]
