import os
import redis

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

# Optional: test connection at startup
try:
    redis_client.ping()
    print("✅ Connected to Redis")
except redis.ConnectionError:
    print("❌ Failed to connect to Redis")
