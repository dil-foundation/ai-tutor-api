# Use the official Python slim image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies including ffmpeg and git
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && apt-get clean

# Copy the requirements file
COPY requirements_optimized.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_optimized.txt

# Copy the application code
COPY app/ app/

# Create credentials directory (for backward compatibility)
RUN mkdir -p /app/credentials

# Set environment variable to locate Google credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json

# Set OpenTelemetry environment variables for containerized environment
ENV OTEL_SERVICE_NAME=ai-tutor-backend
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
ENV OTEL_EXPORTER_OTLP_PROTOCOL=grpc

# Expose the FastAPI default port
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]