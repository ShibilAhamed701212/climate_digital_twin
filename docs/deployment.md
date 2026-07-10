# Deployment Guide

The BHAI platform is deployed as a Docker container for benchmark execution. The deployment uses a minimal `python:3.10-slim` base image with system dependencies for compilation.

## Docker Setup

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml .
COPY runtime/ runtime/
COPY climate/ climate/
COPY copilot/ copilot/

# Install
RUN pip install --no-cache-dir -e ".[dev]"

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import runtime"

CMD ["pytest", "runtime/benchmarks/", "-v", "--benchmark", "--tb=short"]
```

### Docker Compose

```yaml
# docker-compose.benchmark.yml
version: '3.8'
services:
  runtime-benchmark:
    build:
      context: .
      dockerfile: Dockerfile.benchmark
    volumes:
      - ./reports:/reports
    environment:
      - PYTHONUNBUFFERED=1
      - BENCHMARK_ITERATIONS=100
    command: >
      sh -c "python -m pytest runtime/benchmarks/ -v --benchmark --tb=short
             -o 'addopts=' 2>&1 | tee /reports/benchmark_output.txt"
```

## Container Management

### Build

```bash
docker compose -f docker-compose.benchmark.yml build
```

### Run

```bash
docker compose -f docker-compose.benchmark.yml up
```

### View Results

Results are written to `reports/benchmark_output.txt` on the host via the mounted volume.

```bash
cat reports/benchmark_output.txt
```

### Health Check

```bash
docker inspect --format='{{json .State.Health}}' $(docker compose ps -q runtime-benchmark)
```

### Cleanup

```bash
docker compose -f docker-compose.benchmark.yml down
docker compose -f docker-compose.benchmark.yml down --volumes  # Remove volumes
```

## Docker cp Workflow

For running ad-hoc commands inside the container:

```bash
# Copy files into container
docker cp ./runtime/benchmarks/test_e2e_benchmarks.py \
    $(docker compose ps -q runtime-benchmark):/app/runtime/benchmarks/

# Copy results out
docker cp $(docker compose ps -q runtime-benchmark):/reports/benchmark_output.txt \
    ./reports/
```

## Benchmark Execution

67 benchmark tests across 8 suites (WP1-WP8):

```bash
# All benchmarks
pytest runtime/benchmarks/ -v

# Specific suite
pytest runtime/benchmarks/test_e2e_benchmarks.py -v

# With benchmark metrics
pytest runtime/benchmarks/ -v --benchmark
```

## Known Issues

- The Docker image uses Python 3.10 while `pyproject.toml` requires >=3.11. This is a known inconsistency flagged in the security audit (see `docs/security.md`).
- pip and wheel in the Docker image have 8 known CVEs in the build toolchain. Upgrade with `pip install --upgrade pip wheel`.

## Deployment Architecture

See `reports/diagrams/deployment.md` for the full Mermaid deployment diagram.
