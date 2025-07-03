# Use official Python slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies: ffmpeg for audio, git (if needed), and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies early for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and credentials
COPY app/ app/
COPY credentials/ credentials/
COPY .env .

# Set Google credentials environment variable
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json

# Expose port 8000
EXPOSE 8000

# Run FastAPI with uvicorn (WebSockets are supported by default)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
