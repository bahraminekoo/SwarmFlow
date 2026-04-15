FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /app/data

# Expose dashboard port
EXPOSE 8080

# Default: run the CLI
ENTRYPOINT ["swarmflow"]
CMD ["--help"]
