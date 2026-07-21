FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PROOFRELAY_RUN_ROOT=/tmp/proofrelay-runs

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn proofrelay.webapp:app --host 0.0.0.0 --port ${PORT}"]
