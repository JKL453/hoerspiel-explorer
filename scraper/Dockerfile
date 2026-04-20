FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projektcode
COPY src/ src/
COPY app.py run_scraper.py ./
COPY templates/ templates/

# data-Verzeichnis wird als Volume gemountet
VOLUME ["/app/data"]

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "run_scraper.py"]