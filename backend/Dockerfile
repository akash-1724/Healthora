FROM python:3.11-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=240 \
    PIP_RETRIES=15 \
    POETRY_REQUESTS_TIMEOUT=240

RUN pip install --no-cache-dir poetry

COPY backend/pyproject.toml ./pyproject.toml
RUN poetry config virtualenvs.create false && success=0; for i in 1 2 3; do poetry install --no-interaction --no-ansi && success=1 && break; echo "Poetry install failed, retry $i/3"; sleep 10; done; if [ "$success" -ne 1 ]; then echo "Poetry install failed after retries"; exit 1; fi

COPY backend/ ./
COPY ["HIS (1).xlsx", "/app/HIS (1).xlsx"]

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
