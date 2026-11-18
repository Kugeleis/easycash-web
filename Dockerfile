FROM ghcr.io/astral-sh/uv:python3.15-trixie-slim AS builder

WORKDIR /app

# Copy pyproject.toml and uv.lock
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .

# Install dependencies (skip installing local project for now)
RUN uv sync --no-dev --no-install-project

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY static/ ./static/
COPY docs/ ./docs/

# Build the app (this creates the uv-locked environment)
RUN uv run python -c "import easycash_web; print('✅ app initialized')"

# Runtime stage
FROM ghcr.io/astral-sh/uv:python3.15-trixie-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/scripts/ ./scripts/
COPY --from=builder /app/static/ ./static/
COPY --from=builder /app/docs/ ./docs/

# Set PATH to use uv-managed Python
ENV PATH="/app/.venv/bin:$PATH"

# Expose FastAPI default port
EXPOSE 8000

# Run the app
CMD ["uv", "run", "uvicorn", "easycash_web.api:app", "--host", "0.0.0.0", "--port", "8000"]
