"""
Connection Pool Manager for Pre-warmed HTTP Connections

Maintains persistent HTTP/2 connections to external services
to eliminate connection establishment overhead (200-500ms per request).
"""

import aiohttp
import asyncio
from typing import Optional
from app.config import ELEVEN_API_KEY, OPENAI_API_KEY
import httpx

class PreWarmedConnections:
    """
    Manages persistent connections to external services.
    Eliminates connection overhead (200-500ms per request).
    
    Note: ElevenLabs SDK already handles connection pooling internally,
    but this provides additional optimization for direct HTTP calls.
    """
    
    def __init__(self):
        self.elevenlabs_client: Optional[aiohttp.ClientSession] = None
        self.openai_client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize all connection pools (call on server startup)"""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:
                return
            
            print("🔥 [CONN_POOL] Initializing pre-warmed connections...")
            
            try:
                # ElevenLabs connection pool (for direct HTTP calls if needed)
                connector = aiohttp.TCPConnector(
                    limit=100,  # Max 100 connections
                    limit_per_host=20,  # Max 20 per host
                    keepalive_timeout=300,  # 5 minutes
                    enable_cleanup_closed=True,
                    ttl_dns_cache=300,  # DNS cache for 5 minutes
                )
                
                timeout = aiohttp.ClientTimeout(total=30, connect=5)
                self.elevenlabs_client = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "xi-api-key": ELEVEN_API_KEY,
                    }
                )
                
                # OpenAI connection pool (if using OpenAI directly)
                if OPENAI_API_KEY:
                    self.openai_client = httpx.AsyncClient(
                        http2=True,  # HTTP/2 for better performance
                        limits=httpx.Limits(
                            max_keepalive_connections=20,
                            max_connections=100,
                            keepalive_expiry=300,
                        ),
                        timeout=httpx.Timeout(30.0, connect=5.0),
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                        }
                    )
                
                # Warm connections with a test request
                await self._warm_connections()
                
                self._initialized = True
                print("✅ [CONN_POOL] Pre-warmed connections ready")
            except Exception as e:
                print(f"⚠️ [CONN_POOL] Warning: Connection pool initialization failed: {e}")
                # Continue anyway - connections will be established on first use
    
    async def _warm_connections(self):
        """Send test requests to warm up connections"""
        try:
            # Warm ElevenLabs (lightweight HEAD request)
            if self.elevenlabs_client:
                async with self.elevenlabs_client.head("https://api.elevenlabs.io/v1/models") as resp:
                    await resp.read()  # Read response to complete connection
                print("🔥 [CONN_POOL] ElevenLabs connection warmed")
            
            # Warm OpenAI (if configured)
            if self.openai_client:
                await self.openai_client.get("https://api.openai.com/v1/models", params={"limit": 1})
                print("🔥 [CONN_POOL] OpenAI connection warmed")
                
        except Exception as e:
            print(f"⚠️ [CONN_POOL] Warning: Connection warmup failed: {e}")
            # Continue anyway - connections will be established on first use
    
    def get_elevenlabs_client(self) -> Optional[aiohttp.ClientSession]:
        """Get pre-warmed ElevenLabs client (for direct HTTP calls)"""
        return self.elevenlabs_client
    
    def get_openai_client(self) -> Optional[httpx.AsyncClient]:
        """Get pre-warmed OpenAI client"""
        return self.openai_client
    
    async def close(self):
        """Close all connections (call on server shutdown)"""
        if self.elevenlabs_client:
            await self.elevenlabs_client.close()
        if self.openai_client:
            await self.openai_client.aclose()
        self._initialized = False
        print("🔌 [CONN_POOL] All connections closed")

# Global instance
connection_pool = PreWarmedConnections()

