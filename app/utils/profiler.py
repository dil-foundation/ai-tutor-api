"""
Performance Profiler Utility

This module provides performance tracking and profiling capabilities for the AI Tutor backend.
It helps monitor execution times and identify performance bottlenecks in real-time operations.
"""

import time
from typing import Dict, List, Optional
from datetime import datetime

class Profiler:
    """
    Performance profiler for tracking execution times and bottlenecks.
    
    Usage:
        profiler = Profiler()
        profiler.mark("step1")
        # ... do work ...
        profiler.mark("step2")
        profiler.summary()
    """
    
    def __init__(self, name: str = "Profiler"):
        self.name = name
        self.start_time = time.time()
        self.marks: List[Dict] = []
        self.last_mark_time = self.start_time
        
    def mark(self, label: str, description: Optional[str] = None):
        """
        Mark a point in time with a label.
        
        Args:
            label (str): Label for this mark
            description (str, optional): Additional description
        """
        current_time = time.time()
        elapsed_since_start = (current_time - self.start_time) * 1000  # ms
        elapsed_since_last = (current_time - self.last_mark_time) * 1000  # ms
        
        mark_data = {
            "label": label,
            "description": description,
            "timestamp": current_time,
            "elapsed_since_start": elapsed_since_start,
            "elapsed_since_last": elapsed_since_last,
            "datetime": datetime.now().isoformat()
        }
        
        self.marks.append(mark_data)
        self.last_mark_time = current_time
        
        # Log the mark
        print(f"⏱️ [{self.name}] {label}: {elapsed_since_last:.2f}ms (total: {elapsed_since_start:.2f}ms)")
        
    def summary(self, detailed: bool = False):
        """
        Print a summary of all marks.
        
        Args:
            detailed (bool): Whether to print detailed information
        """
        if not self.marks:
            print(f"📊 [{self.name}] No marks recorded")
            return
            
        total_time = (time.time() - self.start_time) * 1000
        
        print(f"\n📊 [{self.name}] Performance Summary:")
        print(f"   Total execution time: {total_time:.2f}ms")
        print(f"   Number of marks: {len(self.marks)}")
        
        if detailed:
            print(f"\n   Detailed breakdown:")
            for i, mark in enumerate(self.marks):
                print(f"   {i+1:2d}. {mark['label']:30s} {mark['elapsed_since_last']:8.2f}ms")
                if mark['description']:
                    print(f"       {mark['description']}")
        
        if len(self.marks) > 1:
            slowest_marks = sorted(self.marks, key=lambda x: x['elapsed_since_last'], reverse=True)[:3]
            print(f"\n   🐌 Slowest operations:")
            for i, mark in enumerate(slowest_marks):
                print(f"   {i+1}. {mark['label']}: {mark['elapsed_since_last']:.2f}ms")
        
        print()
        
    def get_stats(self) -> Dict:
        """
        Get performance statistics as a dictionary.
        
        Returns:
            dict: Performance statistics
        """
        if not self.marks:
            return {
                "total_time": 0,
                "mark_count": 0,
                "marks": [],
                "slowest_operations": []
            }
            
        total_time = (time.time() - self.start_time) * 1000
        slowest_marks = sorted(self.marks, key=lambda x: x['elapsed_since_last'], reverse=True)[:3]
        
        return {
            "total_time": total_time,
            "mark_count": len(self.marks),
            "marks": self.marks,
            "slowest_operations": [
                {
                    "label": mark['label'],
                    "time": mark['elapsed_since_last'],
                    "description": mark['description']
                }
                for mark in slowest_marks
            ]
        }
        
    def reset(self):
        """Reset the profiler to start fresh."""
        self.start_time = time.time()
        self.marks = []
        self.last_mark_time = self.start_time
        print(f"🔄 [{self.name}] Profiler reset")

# Global profiler instance for quick access
_global_profiler = None

def get_global_profiler() -> Profiler:
    """Get the global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = Profiler("Global")
    return _global_profiler

def mark_global(label: str, description: Optional[str] = None):
    """Mark a point using the global profiler."""
    get_global_profiler().mark(label, description)

def summary_global(detailed: bool = False):
    """Print summary using the global profiler."""
    get_global_profiler().summary(detailed)

def reset_global():
    """Reset the global profiler."""
    get_global_profiler().reset()
