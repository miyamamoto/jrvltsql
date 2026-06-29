FROM python:3.12-slim

LABEL maintainer="JLTSQL Contributors"
LABEL description="JRVLTSQL - JRA-VAN DataLab ETL (Linux/headless mode)"

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cache layer)
COPY pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py && \
    pip install --no-cache-dir ".[postgres,s3]" && \
    rm -rf src

# Copy source and install package
COPY . .
RUN pip install --no-cache-dir -e ".[postgres,s3]"

# Default data directory
RUN mkdir -p /app/data

ENV JLTSQL_HEADLESS=1
ENV PYTHONUNBUFFERED=1

# On Linux, only cache-import and PostgreSQL operations are available.
# JV-Link COM (live data fetching) requires Windows.
ENTRYPOINT ["jltsql"]
CMD ["--help"]
