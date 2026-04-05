# Build from the repo root: docker build -f backend/Dockerfile .
FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies for OpenCV
RUN dnf install -y mesa-libGL && dnf clean all

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and install
COPY backend/pyproject.toml ./
RUN uv pip install --system --no-cache .

# Copy shared core package (used by both CLI and web)
COPY src/etsy_assistant/ ${LAMBDA_TASK_ROOT}/src/etsy_assistant/

# Copy web API layer
COPY backend/src/api/ ${LAMBDA_TASK_ROOT}/src/api/

# Set Python path so imports work
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/src"

# Lambda handler
CMD ["api.main.handler"]
