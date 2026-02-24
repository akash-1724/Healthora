FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "until alembic upgrade head; do echo 'Waiting for database...'; sleep 2; done; uvicorn main:app --host 0.0.0.0 --port 8000"]
