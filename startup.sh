#!/bin/bash

echo "=========================================="
echo "🚀 CONTAINER STARTUP SCRIPT"
echo "=========================================="
echo "Timestamp: $(date)"
echo "Container ID: $(hostname)"
echo "Working Directory: $(pwd)"
echo "Python Version: $(python --version)"
echo "=========================================="

echo "📁 Directory Contents:"
ls -la /app/

echo "=========================================="
echo "🔍 Environment Variables:"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
echo "SUPABASE_URL: ${SUPABASE_URL}"
echo "REDIS_HOST: ${REDIS_HOST}"
echo "ELEVEN_API_KEY: ${ELEVEN_API_KEY:0:10}..."
echo "GOOGLE_APPLICATION_CREDENTIALS_JSON: ${GOOGLE_APPLICATION_CREDENTIALS_JSON:0:50}..."
echo "=========================================="

echo "🔍 Network Configuration:"
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -i 2>/dev/null || echo 'N/A')"
echo "Port 8000 status:"
netstat -ln | grep :8000 || echo "Port 8000 not yet bound"

echo "=========================================="
echo "🚀 Starting FastAPI Application..."
echo "=========================================="

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=* --log-level info --access-log
