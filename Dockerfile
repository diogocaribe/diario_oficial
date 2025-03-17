FROM python:3.12-slim

# Install system dependencies including PostgreSQL dev packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    gnupg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry

VOLUME [ "/diario_oficial" ]

# Set working directory
WORKDIR /diario_oficial

# Copy application code
COPY . /diario_oficial

# Install dependencies
RUN poetry install

# Command to run the application
ENTRYPOINT ["poetry", "run", "python", "diario_oficial/cli.py"]