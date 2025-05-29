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

# Copy the entire app including code and credentials
COPY . .

# Set environment variable to locate Google credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json

# Expose the FastAPI default port
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
