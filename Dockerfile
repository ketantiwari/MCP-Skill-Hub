# --- Builder Stage ---
FROM python:3.11-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build tools, curl, and Node.js for dependency compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies into user site-packages
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Runner Stage ---
FROM python:3.11-slim AS runner

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/home/appuser/.local/bin:$PATH"

# Install Node.js on the runner since Reflex frontend relies on Next.js at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy installed python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appgroup /home/appuser/.local

# Copy application source code and configs
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup rxconfig.py pyproject.toml requirements.txt ./

# Setup persistent workspace directories and ensure correct ownership
RUN mkdir -p workspace/logs workspace/runtime workspace/tools && \
    chown -R appuser:appgroup /app

USER appuser

# Expose Reflex UI ports (3030 frontend, 8030 backend)
EXPOSE 3030 8030

# Default container entry point runs the FastMCP server
CMD ["python", "-m", "dynamic_mcp_skill_hub.main"]
