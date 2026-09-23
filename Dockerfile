# Stage A backend image (local stand only).
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts/docker_entrypoint.py /docker_entrypoint.py

RUN pip install --upgrade pip \
    && pip install . "uvicorn[standard]==0.35.0"

EXPOSE 8000

ENTRYPOINT ["python", "/docker_entrypoint.py"]
