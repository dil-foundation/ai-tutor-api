"""
Enhanced Performance Monitor

Tracks detailed metrics for each pipeline step with thresholds and alerts.
Helps identify bottlenecks and measure optimization impact.
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class StepMetrics:
    """Metrics for a single pipeline step"""
    name: str
    durations: List[float] = field(default_factory=list)
    count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    threshold: float = 5.0  # Alert if exceeds this (seconds)
    
    def add_duration(self, duration: float):
        """Add a new duration measurement"""
        self.durations.append(duration)
        self.count += 1
        self.total_time += duration
        self.avg_time = self.total_time / self.count
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        
        # Keep only last 100 samples to prevent memory growth
        if len(self.durations) > 100:
            self.durations.pop(0)
        
        # Alert if exceeds threshold
        if duration > self.threshold:
            print(f"⚠️ [PERF] {self.name} took {duration:.2f}s (threshold: {self.threshold}s)")

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Tracks:
    - Response times for each step
    - Cache hit rates
    - API call latencies
    - Overall pipeline performance
    """
    
    def __init__(self):
        self.steps: Dict[str, StepMetrics] = {}
        self.thresholds = {
            "stt": 2.0,
            "analysis": 3.0,
            "tts": 1.5,
            "total": 5.0,
            "cache_lookup": 0.01,  # 10ms
            "network_transmission": 1.0,
            "audio_decode": 0.5,
            "audio_compression": 0.3,
        }
        self.session_start = time.perf_counter()
        self.request_count = 0
    
    def mark(self, step_name: str, duration: Optional[float] = None):
        """Mark a step completion (backward compatible with Profiler)"""
        if step_name not in self.steps:
            threshold = self.thresholds.get(step_name, 5.0)
            self.steps[step_name] = StepMetrics(name=step_name, threshold=threshold)
        
        if duration is not None:
            self.steps[step_name].add_duration(duration)
    
    async def time_step(self, step_name: str, func, *args, **kwargs):
        """Time a function execution"""
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            self.mark(step_name, duration)
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            self.mark(step_name, duration)
            raise
    
    def get_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        summary = {
            "overall": {
                "total_requests": self.request_count,
                "session_duration": time.perf_counter() - self.session_start,
            },
            "steps": {},
            "bottlenecks": [],
        }
        
        for step_name, metrics in self.steps.items():
            if metrics.count > 0:
                summary["steps"][step_name] = {
                    "count": metrics.count,
                    "avg_ms": round(metrics.avg_time * 1000, 2),
                    "min_ms": round(metrics.min_time * 1000, 2),
                    "max_ms": round(metrics.max_time * 1000, 2),
                    "total_ms": round(metrics.total_time * 1000, 2),
                    "threshold_ms": round(metrics.threshold * 1000, 2),
                }
                
                # Identify bottlenecks
                if metrics.avg_time > metrics.threshold:
                    summary["bottlenecks"].append({
                        "step": step_name,
                        "avg_time": metrics.avg_time,
                        "threshold": metrics.threshold,
                        "excess": metrics.avg_time - metrics.threshold,
                    })
        
        return summary
    
    def print_summary(self):
        """Print formatted performance summary"""
        summary = self.get_summary()
        print("\n" + "="*70)
        print("📊 PERFORMANCE SUMMARY")
        print("="*70)
        
        if not summary["steps"]:
            print("No metrics collected yet.")
            print("="*70 + "\n")
            return
        
        for step_name, data in summary["steps"].items():
            status = "✅" if data["avg_ms"] < data["threshold_ms"] else "⚠️"
            print(f"{status} {step_name:25s} | "
                  f"Avg: {data['avg_ms']:7.2f}ms | "
                  f"Min: {data['min_ms']:7.2f}ms | "
                  f"Max: {data['max_ms']:7.2f}ms | "
                  f"Count: {data['count']:4d}")
        
        if summary["bottlenecks"]:
            print("\n⚠️ BOTTLENECKS DETECTED:")
            for bottleneck in summary["bottlenecks"]:
                excess_ms = (bottleneck['excess'] * 1000)
                print(f"  - {bottleneck['step']}: "
                      f"{bottleneck['avg_time']*1000:.2f}ms "
                      f"(exceeds threshold by {excess_ms:.2f}ms)")
        
        print("="*70 + "\n")
    
    def reset(self):
        """Reset all metrics (useful for testing)"""
        self.steps.clear()
        self.request_count = 0
        self.session_start = time.perf_counter()

# Global instance
performance_monitor = PerformanceMonitor()

