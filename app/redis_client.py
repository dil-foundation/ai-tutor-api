import os
import redis
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global variables
redis_client = None
REDIS_AVAILABLE = False

def initialize_redis():
    """Initialize Redis connection with proper error handling"""
    global redis_client, REDIS_AVAILABLE
    
    try:
        print("🔧 [REDIS] Initializing Redis connection...")
        logger.info("🔧 [REDIS] Initializing Redis connection...")
        
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_username = os.getenv("REDIS_USERNAME", "")
        redis_password = os.getenv("REDIS_PASSWORD", "")
        redis_use_tls = os.getenv("REDIS_USE_TLS", "false").lower() == "true"
        
        print(f"🔧 [REDIS] Connecting to {redis_host}:{redis_port}")
        logger.info(f"🔧 [REDIS] Connecting to {redis_host}:{redis_port}")
        
        # Configure Redis connection with authentication if provided
        redis_config = {
            "host": redis_host,
            "port": redis_port,
            "db": 0,
            "decode_responses": True,
            "socket_connect_timeout": 10,  # Increased timeout for MemoryDB
            "socket_timeout": 10,
            "retry_on_timeout": True,
            "health_check_interval": 30
        }
        
        # Add TLS configuration for MemoryDB
        if redis_use_tls:
            import ssl
            redis_config.update({
                "ssl": True,  # Enable TLS for MemoryDB
                "ssl_check_hostname": False,  # AWS MemoryDB certificates
                "ssl_cert_reqs": ssl.CERT_NONE  # Don't verify SSL certificates for AWS MemoryDB
            })
            print("🔧 [REDIS] Using TLS connection for MemoryDB")
            logger.info("🔧 [REDIS] Using TLS connection for MemoryDB")
        
        # Add authentication if username/password are provided
        if redis_username and redis_password:
            redis_config["username"] = redis_username
            redis_config["password"] = redis_password
            print(f"🔧 [REDIS] Using authentication with username: {redis_username}")
            logger.info(f"🔧 [REDIS] Using authentication with username: {redis_username}")
        
        redis_client = redis.Redis(**redis_config)
        
        # Test connection
        redis_client.ping()
        REDIS_AVAILABLE = True
        print("✅ [REDIS] Successfully connected to Redis")
        logger.info("✅ [REDIS] Successfully connected to Redis")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ [REDIS] Failed to connect to Redis: {e}")
        logger.error(f"❌ [REDIS] Failed to connect to Redis: {e}")
        REDIS_AVAILABLE = False
        return False
    except Exception as e:
        print(f"❌ [REDIS] Unexpected Redis error: {e}")
        logger.error(f"❌ [REDIS] Unexpected Redis error: {e}")
        REDIS_AVAILABLE = False
        return False

def get_redis_client():
    """Get Redis client with availability check"""
    if not REDIS_AVAILABLE:
        logger.warning("⚠️ [REDIS] Redis not available, operations will be skipped")
        return None
    return redis_client

def is_redis_available():
    """Check if Redis is available"""
    return REDIS_AVAILABLE

# Initialize Redis connection (non-blocking)
initialize_redis()
