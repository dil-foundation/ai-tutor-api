#!/usr/bin/env python3
"""
Performance Testing Script for AI Tutor API Optimizations
Run this script to compare performance before and after optimizations
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import List, Dict, Any
import argparse

class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, method: str = "GET", 
                          data: Dict = None, headers: Dict = None,
                          iterations: int = 5) -> Dict[str, Any]:
        """Test a single endpoint multiple times and return performance metrics"""
        
        if headers is None:
            headers = {"Content-Type": "application/json"}
            
        times = []
        errors = []
        
        print(f"🔄 Testing {method} {endpoint} ({iterations} iterations)...")
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                if method.upper() == "GET":
                    async with self.session.get(f"{self.base_url}{endpoint}", 
                                              headers=headers) as response:
                        await response.json()
                        status = response.status
                elif method.upper() == "POST":
                    async with self.session.post(f"{self.base_url}{endpoint}",
                                               json=data, headers=headers) as response:
                        await response.json()
                        status = response.status
                
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if status == 200:
                    times.append(duration)
                    print(f"  ✅ Iteration {i+1}: {duration:.0f}ms")
                else:
                    errors.append(f"HTTP {status}")
                    print(f"  ❌ Iteration {i+1}: HTTP {status}")
                    
            except Exception as e:
                errors.append(str(e))
                print(f"  ❌ Iteration {i+1}: {str(e)}")
        
        if not times:
            return {
                "endpoint": endpoint,
                "method": method,
                "success": False,
                "error": "No successful requests",
                "errors": errors
            }
        
        return {
            "endpoint": endpoint,
            "method": method,
            "success": True,
            "iterations": len(times),
            "avg_time_ms": round(statistics.mean(times), 2),
            "min_time_ms": round(min(times), 2),
            "max_time_ms": round(max(times), 2),
            "median_time_ms": round(statistics.median(times), 2),
            "std_dev_ms": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
            "errors": errors,
            "raw_times": times
        }
    
    async def compare_endpoints(self, old_endpoint: str, new_endpoint: str,
                              method: str = "GET", data: Dict = None,
                              headers: Dict = None, iterations: int = 5) -> Dict[str, Any]:
        """Compare performance between old and new endpoints"""
        
        print(f"\n🔍 PERFORMANCE COMPARISON")
        print(f"Old endpoint: {old_endpoint}")
        print(f"New endpoint: {new_endpoint}")
        print("=" * 60)
        
        # Test both endpoints
        old_results = await self.test_endpoint(old_endpoint, method, data, headers, iterations)
        new_results = await self.test_endpoint(new_endpoint, method, data, headers, iterations)
        
        # Calculate improvement
        if old_results["success"] and new_results["success"]:
            old_avg = old_results["avg_time_ms"]
            new_avg = new_results["avg_time_ms"]
            
            improvement_ms = old_avg - new_avg
            improvement_percent = (improvement_ms / old_avg) * 100
            
            comparison = {
                "old_endpoint": old_results,
                "new_endpoint": new_results,
                "improvement": {
                    "time_saved_ms": round(improvement_ms, 2),
                    "percent_faster": round(improvement_percent, 2),
                    "speedup_factor": round(old_avg / new_avg, 2)
                }
            }
            
            print(f"\n📊 RESULTS:")
            print(f"Old endpoint average: {old_avg:.0f}ms")
            print(f"New endpoint average: {new_avg:.0f}ms")
            print(f"Time saved: {improvement_ms:.0f}ms")
            print(f"Performance improvement: {improvement_percent:.1f}% faster")
            print(f"Speedup factor: {old_avg / new_avg:.1f}x")
            
            if improvement_percent > 50:
                print("🚀 EXCELLENT: Major performance improvement!")
            elif improvement_percent > 20:
                print("✅ GOOD: Significant performance improvement!")
            elif improvement_percent > 0:
                print("👍 OK: Minor performance improvement")
            else:
                print("⚠️ WARNING: New endpoint is slower!")
                
        else:
            comparison = {
                "old_endpoint": old_results,
                "new_endpoint": new_results,
                "improvement": None,
                "error": "One or both endpoints failed"
            }
            print("❌ COMPARISON FAILED: One or both endpoints had errors")
        
        return comparison

async def main():
    parser = argparse.ArgumentParser(description='Performance test AI Tutor API endpoints')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL of the API server')
    parser.add_argument('--iterations', type=int, default=5,
                       help='Number of test iterations per endpoint')
    parser.add_argument('--auth-token', help='Authentication token for protected endpoints')
    
    args = parser.parse_args()
    
    # Set up headers with auth token if provided
    headers = {"Content-Type": "application/json"}
    if args.auth_token:
        headers["Authorization"] = f"Bearer {args.auth_token}"
    
    async with PerformanceTester(args.base_url) as tester:
        print("🚀 AI Tutor API Performance Testing")
        print("=" * 50)
        
        # Test cases for comparison
        test_cases = [
            {
                "name": "Progress Overview",
                "old": "/teacher/dashboard/progress-overview?time_range=all_time",
                "new": "/teacher/optimized/dashboard/progress-overview-fast?time_range=all_time",
                "method": "GET"
            },
            {
                "name": "Progress Metrics", 
                "old": "/teacher/dashboard/progress-metrics?time_range=all_time",
                "new": "/teacher/optimized/dashboard/progress-metrics-fast?time_range=all_time",
                "method": "GET"
            },
            {
                "name": "Batch Dashboard Data",
                "old": None,  # No direct equivalent - would be multiple requests
                "new": "/teacher/optimized/dashboard/batch-data",
                "method": "GET"
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"🧪 Testing: {test_case['name']}")
            print(f"{'='*60}")
            
            if test_case["old"]:
                # Compare old vs new
                comparison = await tester.compare_endpoints(
                    test_case["old"],
                    test_case["new"], 
                    test_case["method"],
                    headers=headers,
                    iterations=args.iterations
                )
                results.append({
                    "test_name": test_case["name"],
                    "type": "comparison",
                    "results": comparison
                })
            else:
                # Test new endpoint only
                new_results = await tester.test_endpoint(
                    test_case["new"],
                    test_case["method"],
                    headers=headers,
                    iterations=args.iterations
                )
                results.append({
                    "test_name": test_case["name"],
                    "type": "new_only",
                    "results": new_results
                })
                
                print(f"\n📊 RESULTS for {test_case['name']}:")
                if new_results["success"]:
                    print(f"Average response time: {new_results['avg_time_ms']:.0f}ms")
                    print(f"Min/Max: {new_results['min_time_ms']:.0f}ms / {new_results['max_time_ms']:.0f}ms")
                else:
                    print(f"❌ Failed: {new_results.get('error', 'Unknown error')}")
        
        # Generate summary report
        print(f"\n{'='*60}")
        print("📋 PERFORMANCE TEST SUMMARY")
        print(f"{'='*60}")
        
        total_improvements = []
        
        for result in results:
            test_name = result["test_name"]
            
            if result["type"] == "comparison":
                comparison = result["results"]
                if comparison.get("improvement"):
                    improvement = comparison["improvement"]["percent_faster"]
                    total_improvements.append(improvement)
                    
                    print(f"\n🧪 {test_name}:")
                    print(f"   Improvement: {improvement:.1f}% faster")
                    print(f"   Time saved: {comparison['improvement']['time_saved_ms']:.0f}ms")
                    
            elif result["type"] == "new_only":
                new_results = result["results"]
                if new_results["success"]:
                    print(f"\n🧪 {test_name} (New endpoint only):")
                    print(f"   Average time: {new_results['avg_time_ms']:.0f}ms")
        
        if total_improvements:
            avg_improvement = statistics.mean(total_improvements)
            print(f"\n🎯 OVERALL PERFORMANCE IMPROVEMENT: {avg_improvement:.1f}% faster")
            
            if avg_improvement > 70:
                print("🚀 OUTSTANDING: Massive performance gains!")
            elif avg_improvement > 50:
                print("🎉 EXCELLENT: Major performance improvements!")
            elif avg_improvement > 30:
                print("✅ VERY GOOD: Significant improvements!")
            elif avg_improvement > 10:
                print("👍 GOOD: Noticeable improvements!")
            else:
                print("📈 MINOR: Small improvements!")
        
        # Save detailed results to file
        timestamp = int(time.time())
        filename = f"performance_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "test_config": {
                    "base_url": args.base_url,
                    "iterations": args.iterations
                },
                "results": results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")
        print("\n✅ Performance testing completed!")

if __name__ == "__main__":
    asyncio.run(main())
