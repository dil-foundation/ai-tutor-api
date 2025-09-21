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
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ app/

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Create credentials directory (for backward compatibility)
RUN mkdir -p /app/credentials

# Remove the hardcoded GOOGLE_APPLICATION_CREDENTIALS environment variable
# This will be set dynamically in the application code

# Set OpenTelemetry environment variables for containerized environment
ENV OTEL_SERVICE_NAME=ai-tutor-backend
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
ENV OTEL_EXPORTER_OTLP_PROTOCOL=grpc

# Expose the FastAPI default port
EXPOSE 8000

# Start the FastAPI app using startup script
CMD ["/app/startup.sh"]