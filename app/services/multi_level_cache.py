"""
Multi-Level Cache Service for AI English Tutor

Implements a three-tier caching strategy:
- L1: Exact phrase matches with pre-generated audio (100ms response)
- L2: Pattern-based matches with pre-generated audio (500ms response)
- L3: Stage templates with on-demand generation (fallback)

This service extends the predictive cache with audio pre-generation
and intelligent cache warming for optimal performance.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from app.services.predictive_cache import StageAwareCache, PredictiveResult, _normalize_text


@dataclass
class CachedResponse:
    """Complete cached response with text and pre-generated audio."""
    text: str
    audio: bytes
    stage: str
    source: str  # "l1", "l2", "l3"
    confidence: float
    cache_time: float
    hit_count: int = 0
    topic: Optional[str] = None


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    misses: int = 0
    total_requests: int = 0
    avg_response_time_l1: float = 0.0
    avg_response_time_l2: float = 0.0
    avg_response_time_l3: float = 0.0


class MultiLevelCache:
    """
    Multi-level cache system with pre-generated audio responses.
    
    Architecture:
    - L1 Cache: Exact phrase matches with instant audio (100ms)
    - L2 Cache: Pattern-based matches with cached audio (500ms)
    - L3 Cache: Stage templates (existing predictive cache)
    
    The cache automatically learns from interactions and pre-generates
    audio for frequently used responses to minimize latency.
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,  # 1 hour default TTL
        max_l1_entries: int = 500,
        max_l2_entries: int = 1000,
        l1_audio_cache_size: int = 200,
        l2_audio_cache_size: int = 500,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_l1_entries = max_l1_entries
        self.max_l2_entries = max_l2_entries
        self.l1_audio_cache_size = l1_audio_cache_size
        self.l2_audio_cache_size = l2_audio_cache_size
        
        # L1: Exact phrase cache with audio
        # Key: normalized user input, Value: (response_text, audio_bytes, expiry, hit_count)
        self.l1_cache: Dict[str, Tuple[str, bytes, float, int]] = {}
        
        # L2: Pattern-based cache with audio
        # Key: pattern_hash, Value: (response_text, audio_bytes, expiry, hit_count, pattern)
        self.l2_cache: Dict[str, Tuple[str, bytes, float, int, str]] = {}
        
        # L3: Stage-aware predictive cache (delegates to existing cache)
        self.predictive_cache = StageAwareCache(ttl_seconds=ttl_seconds)
        
        # Statistics tracking
        self.stats = CacheStats()
        self._lock = asyncio.Lock()
        
        # Response time tracking for each level
        self._response_times: Dict[str, List[float]] = {
            "l1": [],
            "l2": [],
            "l3": [],
        }

    def _pattern_hash(self, stage: str, user_input: str, topic: Optional[str]) -> str:
        """Generate a consistent hash for pattern-based caching."""
        normalized = _normalize_text(user_input)
        # Extract key words (first 100 chars for pattern matching)
        pattern_text = normalized[:100]
        topic_part = _normalize_text(topic or "general")
        combined = f"{stage}:{topic_part}:{pattern_text}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _purge_expired_entries(self) -> None:
        """Remove expired entries from L1 and L2 caches.
        Optimized to only purge every 100 requests to reduce overhead.
        """
        # Only purge periodically to avoid overhead on every request
        if self.stats.total_requests % 100 != 0:
            return
        
        now = time.time()
        
        # Purge L1 (only if cache is getting large)
        if len(self.l1_cache) > self.max_l1_entries * 0.8:
            expired_l1 = [
                key for key, (_, _, expiry, _) in self.l1_cache.items()
                if expiry < now
            ]
            for key in expired_l1:
                self.l1_cache.pop(key, None)
        
        # Purge L2 (only if cache is getting large)
        if len(self.l2_cache) > self.max_l2_entries * 0.8:
            expired_l2 = [
                key for key, (_, _, expiry, _, _) in self.l2_cache.items()
                if expiry < now
            ]
            for key in expired_l2:
                self.l2_cache.pop(key, None)

    def _evict_lru_if_needed(self) -> None:
        """Evict least recently used entries if cache is full."""
        now = time.time()
        
        # L1 eviction
        if len(self.l1_cache) >= self.max_l1_entries:
            # Sort by hit count (LRU: lowest hit count first)
            sorted_l1 = sorted(
                self.l1_cache.items(),
                key=lambda x: (x[1][3], x[1][2])  # (hit_count, expiry)
            )
            # Remove 10% of least used entries
            evict_count = max(1, self.max_l1_entries // 10)
            for key, _ in sorted_l1[:evict_count]:
                self.l1_cache.pop(key, None)
        
        # L2 eviction
        if len(self.l2_cache) >= self.max_l2_entries:
            sorted_l2 = sorted(
                self.l2_cache.items(),
                key=lambda x: (x[1][3], x[1][2])  # (hit_count, expiry)
            )
            evict_count = max(1, self.max_l2_entries // 10)
            for key, _ in sorted_l2[:evict_count]:
                self.l2_cache.pop(key, None)

    async def get_cached_response(
        self,
        *,
        stage: str,
        user_input: str,
        user_name: str,
        topic: Optional[str],
        get_audio_fn,  # Function to generate audio if needed
    ) -> Optional[CachedResponse]:
        """
        Multi-level cache lookup with automatic fallback.
        
        Returns:
            CachedResponse if found in any level, None otherwise
        """
        start_time = time.perf_counter()
        self.stats.total_requests += 1
        
        async with self._lock:
            self._purge_expired_entries()
            now = time.time()
            normalized_input = _normalize_text(user_input)
            
            # L1: Exact phrase match (fastest - 100ms)
            if normalized_input in self.l1_cache:
                response_text, audio, expiry, hit_count = self.l1_cache[normalized_input]
                if expiry >= now:
                    # Update hit count
                    self.l1_cache[normalized_input] = (
                        response_text, audio, expiry, hit_count + 1
                    )
                    self.stats.l1_hits += 1
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._response_times["l1"].append(response_time)
                    self._update_avg_response_time("l1", response_time)
                    
                    return CachedResponse(
                        text=response_text,
                        audio=audio,
                        stage=stage,
                        source="l1",
                        confidence=0.95,
                        cache_time=now,
                        hit_count=hit_count + 1,
                        topic=topic,
                    )
            
            # L2: Pattern-based match (medium - 500ms)
            pattern_hash = self._pattern_hash(stage, user_input, topic)
            if pattern_hash in self.l2_cache:
                response_text, audio, expiry, hit_count, pattern = self.l2_cache[pattern_hash]
                if expiry >= now:
                    # Update hit count
                    self.l2_cache[pattern_hash] = (
                        response_text, audio, expiry, hit_count + 1, pattern
                    )
                    self.stats.l2_hits += 1
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._response_times["l2"].append(response_time)
                    self._update_avg_response_time("l2", response_time)
                    
                    return CachedResponse(
                        text=response_text,
                        audio=audio,
                        stage=stage,
                        source="l2",
                        confidence=0.85,
                        cache_time=now,
                        hit_count=hit_count + 1,
                        topic=topic,
                    )
            
            # Don't check L3 here - it's too slow (generates audio synchronously)
            # L3 will be handled separately if needed
            
            # Cache miss
            self.stats.misses += 1
            return None
    
    async def get_cached_response_fast(
        self,
        *,
        stage: str,
        user_input: str,
        topic: Optional[str],
    ) -> Optional[CachedResponse]:
        """
        Fast cache lookup for L1/L2 only (no L3, no audio generation).
        This is optimized for speed and runs in parallel with other operations.
        """
        start_time = time.perf_counter()
        
        # Use a shorter lock scope - only lock during dictionary access
        async with self._lock:
            now = time.time()
            normalized_input = _normalize_text(user_input)
            
            # L1: Exact phrase match (fastest - 100ms)
            if normalized_input in self.l1_cache:
                response_text, audio, expiry, hit_count = self.l1_cache[normalized_input]
                if expiry >= now:
                    self.l1_cache[normalized_input] = (
                        response_text, audio, expiry, hit_count + 1
                    )
                    self.stats.l1_hits += 1
                    self.stats.total_requests += 1
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._response_times["l1"].append(response_time)
                    self._update_avg_response_time("l1", response_time)
                    
                    return CachedResponse(
                        text=response_text,
                        audio=audio,
                        stage=stage,
                        source="l1",
                        confidence=0.95,
                        cache_time=now,
                        hit_count=hit_count + 1,
                        topic=topic,
                    )
            
            # L2: Pattern-based match (medium - 500ms)
            pattern_hash = self._pattern_hash(stage, user_input, topic)
            if pattern_hash in self.l2_cache:
                response_text, audio, expiry, hit_count, pattern = self.l2_cache[pattern_hash]
                if expiry >= now:
                    self.l2_cache[pattern_hash] = (
                        response_text, audio, expiry, hit_count + 1, pattern
                    )
                    self.stats.l2_hits += 1
                    self.stats.total_requests += 1
                    response_time = (time.perf_counter() - start_time) * 1000
                    self._response_times["l2"].append(response_time)
                    self._update_avg_response_time("l2", response_time)
                    
                    return CachedResponse(
                        text=response_text,
                        audio=audio,
                        stage=stage,
                        source="l2",
                        confidence=0.85,
                        cache_time=now,
                        hit_count=hit_count + 1,
                        topic=topic,
                    )
        
        # Cache miss - return None quickly
        self.stats.misses += 1
        self.stats.total_requests += 1
        return None

    async def cache_response(
        self,
        *,
        stage: str,
        user_input: str,
        response_text: str,
        audio: Optional[bytes],  # Can be None if audio not ready yet
        topic: Optional[str],
        cache_level: str = "l2",  # "l1" or "l2"
    ) -> None:
        """
        Cache a response with audio at the specified level.
        This is non-blocking and can be called asynchronously.
        
        Args:
            cache_level: "l1" for exact phrase, "l2" for pattern-based
            audio: Can be None if audio generation is still in progress
        """
        try:
            async with self._lock:
                self._purge_expired_entries()
                self._evict_lru_if_needed()
                
                now = time.time()
                expiry = now + self.ttl_seconds
                normalized_input = _normalize_text(user_input)
                
                if cache_level == "l1":
                    # L1: Exact phrase match
                    if audio:
                        self.l1_cache[normalized_input] = (response_text, audio, expiry, 0)
                        print(f"💾 [MULTI_CACHE] Cached L1: '{user_input[:50]}...' → '{response_text[:50]}...'")
                    else:
                        # Store without audio, will be updated later
                        self.l1_cache[normalized_input] = (response_text, b'', expiry, 0)
                
                elif cache_level == "l2":
                    # L2: Pattern-based
                    pattern_hash = self._pattern_hash(stage, user_input, topic)
                    pattern_text = normalized_input[:100]
                    if audio:
                        self.l2_cache[pattern_hash] = (response_text, audio, expiry, 0, pattern_text)
                        print(f"💾 [MULTI_CACHE] Cached L2: pattern '{pattern_text[:50]}...' → '{response_text[:50]}...'")
                    else:
                        # Store without audio, will be updated later
                        self.l2_cache[pattern_hash] = (response_text, b'', expiry, 0, pattern_text)
        except Exception as e:
            print(f"⚠️ [MULTI_CACHE] Error caching response: {e}")
    
    async def update_cached_audio(
        self,
        *,
        stage: str,
        user_input: str,
        audio: bytes,
        topic: Optional[str],
    ) -> None:
        """
        Update cached response with audio (non-blocking).
        Called after TTS generation completes.
        """
        try:
            async with self._lock:
                normalized_input = _normalize_text(user_input)
                
                # Try L1 first
                if normalized_input in self.l1_cache:
                    response_text, _, expiry, hit_count = self.l1_cache[normalized_input]
                    self.l1_cache[normalized_input] = (response_text, audio, expiry, hit_count)
                    return
                
                # Try L2
                pattern_hash = self._pattern_hash(stage, user_input, topic)
                if pattern_hash in self.l2_cache:
                    response_text, _, expiry, hit_count, pattern = self.l2_cache[pattern_hash]
                    self.l2_cache[pattern_hash] = (response_text, audio, expiry, hit_count, pattern)
        except Exception as e:
            print(f"⚠️ [MULTI_CACHE] Error updating cached audio: {e}")

    def _update_avg_response_time(self, level: str, new_time: float) -> None:
        """Update rolling average response time for a cache level."""
        times = self._response_times[level]
        if len(times) > 100:
            times.pop(0)  # Keep last 100 measurements
        
        if level == "l1":
            self.stats.avg_response_time_l1 = sum(times) / len(times) if times else 0.0
        elif level == "l2":
            self.stats.avg_response_time_l2 = sum(times) / len(times) if times else 0.0
        elif level == "l3":
            self.stats.avg_response_time_l3 = sum(times) / len(times) if times else 0.0

    def get_cache_stats(self) -> Dict[str, any]:
        """Get comprehensive cache statistics."""
        total_hits = self.stats.l1_hits + self.stats.l2_hits + self.stats.l3_hits
        hit_rate = (
            (total_hits / self.stats.total_requests * 100)
            if self.stats.total_requests > 0
            else 0.0
        )
        
        return {
            "l1": {
                "hits": self.stats.l1_hits,
                "entries": len(self.l1_cache),
                "avg_response_time_ms": round(self.stats.avg_response_time_l1, 2),
            },
            "l2": {
                "hits": self.stats.l2_hits,
                "entries": len(self.l2_cache),
                "avg_response_time_ms": round(self.stats.avg_response_time_l2, 2),
            },
            "l3": {
                "hits": self.stats.l3_hits,
                "avg_response_time_ms": round(self.stats.avg_response_time_l3, 2),
            },
            "overall": {
                "total_requests": self.stats.total_requests,
                "total_hits": total_hits,
                "misses": self.stats.misses,
                "hit_rate_percent": round(hit_rate, 2),
            },
        }

    async def warm_cache(
        self,
        common_phrases: List[Tuple[str, str, Optional[str]]],  # (user_input, response, topic)
        get_audio_fn,
        stage: str = "greeting",
    ) -> None:
        """
        Pre-populate cache with common phrases and their audio.
        
        This is called during startup to warm the cache with
        frequently used responses.
        """
        print(f"🔥 [MULTI_CACHE] Warming cache with {len(common_phrases)} common phrases...")
        
        for user_input, response_text, topic in common_phrases:
            try:
                audio = await get_audio_fn(response_text)
                await self.cache_response(
                    stage=stage,
                    user_input=user_input,
                    response_text=response_text,
                    audio=audio,
                    topic=topic,
                    cache_level="l1",  # Common phrases go to L1
                )
            except Exception as e:
                print(f"⚠️ [MULTI_CACHE] Error warming cache for '{user_input}': {e}")
        
        print(f"✅ [MULTI_CACHE] Cache warmed with {len(common_phrases)} entries")

    def clear_cache(self, level: Optional[str] = None) -> None:
        """Clear cache entries. If level is None, clears all levels."""
        if level == "l1" or level is None:
            self.l1_cache.clear()
        if level == "l2" or level is None:
            self.l2_cache.clear()
        if level == "l3" or level is None:
            self.predictive_cache.pattern_cache.clear()
            self.predictive_cache.phrase_cache.clear()
        
        print(f"🧹 [MULTI_CACHE] Cleared {'all caches' if level is None else f'{level} cache'}")

