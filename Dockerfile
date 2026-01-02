FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including ffmpeg for downloads
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY Vocard-Fresh/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY Vocard-Fresh/ .

# Copy production settings (uses env vars for secrets)
COPY Vocard-Fresh/settings.production.json ./settings.json

# Run the bot
CMD ["python", "main.py"]
