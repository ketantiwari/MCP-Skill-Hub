FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONPATH=/app/src

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY workspace ./workspace

CMD ["python", "-m", "dynamic_mcp_skill_hub.main"]
