FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml README.md alembic.ini ./
COPY releaselens ./releaselens
COPY alembic ./alembic
COPY web ./web
COPY data ./data
COPY scripts ./scripts
COPY evaluation ./evaluation
RUN pip install --no-deps . && useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn releaselens.api:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log"]
