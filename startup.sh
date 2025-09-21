#!/bin/bash
set -e

echo "=========================================="
echo "🚀 CONTAINER STARTUP SCRIPT"
echo "=========================================="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Container ID: $(hostname)"
echo "Working Directory: $(pwd)"
echo "Python Version: $(python --version 2>&1)"
echo "Uvicorn Version: $(uvicorn --version 2>&1)"
echo "=========================================="

echo "📁 Directory Contents:"
ls -la /app/

echo "=========================================="
echo "🔍 Environment Variables:"
# List important environment variables, masking sensitive ones
for var in OPENAI_API_KEY SUPABASE_URL SUPABASE_SERVICE_KEY ELEVEN_API_KEY ELEVEN_VOICE_ID REDIS_HOST REDIS_PORT WP_SITE_URL WP_API_USERNAME WP_API_APPLICATION_PASSWORD GOOGLE_APPLICATION_CREDENTIALS_JSON ENVIRONMENT TASK_VERSION; do
  value=$(printenv $var)
  if [ -n "$value" ]; then
    if [[ "$var" == *"KEY"* || "$var" == *"PASSWORD"* || "$var" == *"CREDENTIALS"* ]]; then
      echo "  ✅ $var: ${value:0:10}..." # Mask sensitive values
    else
      echo "  ✅ $var: $value"
    fi
  else
    echo "  ❌ $var: NOT SET"
  fi
done
echo "=========================================="

echo "🔍 Network Configuration:"
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -i 2>/dev/null || echo 'N/A')"
echo "Port 8000 status:"
# Use ss instead of netstat if available
if command -v ss &> /dev/null; then
  ss -ln | grep :8000 || echo "Port 8000 not yet bound"
elif command -v netstat &> /dev/null; then
  netstat -ln | grep :8000 || echo "Port 8000 not yet bound"
else
  echo "Neither ss nor netstat available"
fi
echo "=========================================="

echo "⏳ Testing external service connectivity..."
# Basic connectivity tests
if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
  echo "Testing Redis connectivity to $REDIS_HOST:$REDIS_PORT..."
  if command -v nc &> /dev/null; then
    if nc -z -w 5 "$REDIS_HOST" "$REDIS_PORT"; then
      echo "✅ Redis is reachable"
    else
      echo "❌ Redis is NOT reachable"
    fi
  else
    echo "⚠️ netcat not available, skipping Redis connectivity test"
  fi
else
  echo "ℹ️ Redis host or port not set, skipping Redis connectivity check"
fi

if [ -n "$SUPABASE_URL" ]; then
  echo "Testing Supabase connectivity to $SUPABASE_URL..."
  if command -v curl &> /dev/null; then
    if curl -s --connect-timeout 5 --max-time 10 "$SUPABASE_URL" > /dev/null; then
      echo "✅ Supabase is reachable"
    else
      echo "❌ Supabase is NOT reachable"
    fi
  else
    echo "⚠️ curl not available, skipping Supabase connectivity test"
  fi
else
  echo "ℹ️ Supabase URL not set, skipping connectivity check"
fi
echo "=========================================="

echo "🔐 Setting up Google Cloud credentials..."
if [ -n "$GOOGLE_CREDENTIALS" ]; then
  echo "Writing Google credentials to /app/credentials/google-credentials.json"
  echo "$GOOGLE_CREDENTIALS" > /app/credentials/google-credentials.json
  chmod 600 /app/credentials/google-credentials.json
  echo "✅ Google credentials file created successfully"
else
  echo "❌ GOOGLE_CREDENTIALS environment variable not set"
fi
echo "=========================================="

echo "🐍 Python Environment Check:"
echo "Python executable: $(which python)"
echo "Pip version: $(pip --version 2>&1)"
echo "Installed packages (key ones):"
pip list | grep -E "(fastapi|uvicorn|supabase|redis|openai|elevenlabs)" || echo "Some packages may not be installed"
echo "=========================================="

echo "🚀 Starting FastAPI Application..."
echo "Command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=* --log-level info --access-log"
echo "=========================================="

# Start the FastAPI app with comprehensive logging
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips=* \
  --log-level info \
  --access-log \
  --use-colors \
  --loop asyncio
