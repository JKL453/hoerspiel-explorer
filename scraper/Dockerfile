FROM python:3.13-alpine AS builder

RUN apk add --no-cache gcc musl-dev libxml2-dev libxslt-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.13-alpine

RUN apk add --no-cache libxml2 libxslt

WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ src/
COPY scraper/ scraper/

VOLUME ["/app/data"]

ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 5123

CMD ["python", "-m", "scraper.run_scraper", "--port", "5123"]
