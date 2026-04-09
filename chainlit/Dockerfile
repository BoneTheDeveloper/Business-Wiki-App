FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency files and install
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . .

CMD ["uv", "run", "chainlit", "run", "app.py", "--headless", "--host", "0.0.0.0", "--port", "8000"]
