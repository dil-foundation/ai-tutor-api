import asyncio
import time
import aiohttp
import json
import base64
from typing import Dict, List, Any
import statistics
from app.utils.profiler import Profiler

class PerformanceTester:
    """Performance testing utility for AI Tutor backend"""
    
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def test_websocket_connection(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single websocket connection and measure performance"""
        start_time = time.time()
        profiler = Profiler()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"{self.base_url}/ws/learn") as ws:
                    # Send test data
                    await ws.send_json(test_data)
                    
                    # Receive responses and measure timing
                    responses = []
                    while True:
                        try:
                            msg = await asyncio.wait_for(ws.receive_json(), timeout=30.0)
                            responses.append({
                                "step": msg.get("step"),
                                "timestamp": time.time() - start_time
                            })
                            
                            # Check if we've completed a full cycle
                            if msg.get("step") == "await_next":
                                break
                                
                        except asyncio.TimeoutError:
                            break
                    
                    total_time = time.time() - start_time
                    
                    return {
                        "success": True,
                        "total_time": total_time,
                        "responses": responses,
                        "response_count": len(responses)
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }
    
    async def run_load_test(self, num_connections: int = 10, concurrent: bool = True) -> Dict[str, Any]:
        """Run load test with multiple connections"""
        print(f"🚀 Starting load test with {num_connections} connections...")
        
        # Sample test data (base64 encoded audio)
        test_data = {
            "audio_base64": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT"
        }
        
        if concurrent:
            # Run all connections concurrently
            tasks = [self.test_websocket_connection(test_data) for _ in range(num_connections)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Run connections sequentially
            results = []
            for i in range(num_connections):
                result = await self.test_websocket_connection(test_data)
                results.append(result)
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        if successful_results:
            total_times = [r["total_time"] for r in successful_results]
            response_counts = [r["response_count"] for r in successful_results]
            
            analysis = {
                "total_connections": num_connections,
                "successful_connections": len(successful_results),
                "failed_connections": len(failed_results),
                "success_rate": len(successful_results) / num_connections * 100,
                "avg_response_time": statistics.mean(total_times),
                "min_response_time": min(total_times),
                "max_response_time": max(total_times),
                "std_dev_response_time": statistics.stdev(total_times) if len(total_times) > 1 else 0,
                "avg_responses_per_connection": statistics.mean(response_counts),
                "detailed_results": successful_results
            }
        else:
            analysis = {
                "total_connections": num_connections,
                "successful_connections": 0,
                "failed_connections": len(failed_results),
                "success_rate": 0,
                "error": "No successful connections"
            }
        
        return analysis
    
    async def benchmark_individual_operations(self) -> Dict[str, Any]:
        """Benchmark individual operations (STT, translation, TTS)"""
        print("🔬 Benchmarking individual operations...")
        
        # Test data
        test_audio_base64 = "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT"
        test_text = "آپ نے کہا: میں انگلش سیکھ رہا ہوں اب میرے بعد دہرائیں۔"
        
        results = {}
        
        # Test STT
        try:
            from app.services import stt
            audio_bytes = base64.b64decode(test_audio_base64)
            
            start_time = time.time()
            stt_result = stt.transcribe_audio_bytes_eng(audio_bytes)
            stt_time = time.time() - start_time
            
            results["stt"] = {
                "time": stt_time,
                "success": True,
                "text": stt_result.get("text", "")
            }
        except Exception as e:
            results["stt"] = {
                "time": 0,
                "success": False,
                "error": str(e)
            }
        
        # Test Translation
        try:
            from app.services.translation import translate_urdu_to_english, translate_to_urdu
            
            # Test Urdu to English
            start_time = time.time()
            urdu_to_en = translate_urdu_to_english(test_text)
            urdu_to_en_time = time.time() - start_time
            
            # Test English to Urdu
            start_time = time.time()
            en_to_urdu = translate_to_urdu("I am learning English")
            en_to_urdu_time = time.time() - start_time
            
            results["translation"] = {
                "urdu_to_english_time": urdu_to_en_time,
                "english_to_urdu_time": en_to_urdu_time,
                "success": True,
                "urdu_to_english_result": urdu_to_en,
                "english_to_urdu_result": en_to_urdu
            }
        except Exception as e:
            results["translation"] = {
                "time": 0,
                "success": False,
                "error": str(e)
            }
        
        # Test TTS
        try:
            from app.services.tts import synthesize_speech_bytes
            
            start_time = time.time()
            tts_result = await synthesize_speech_bytes(test_text)
            tts_time = time.time() - start_time
            
            results["tts"] = {
                "time": tts_time,
                "success": True,
                "audio_size_bytes": len(tts_result)
            }
        except Exception as e:
            results["tts"] = {
                "time": 0,
                "success": False,
                "error": str(e)
            }
        
        return results
    
    def print_performance_report(self, load_test_results: Dict[str, Any], benchmark_results: Dict[str, Any]):
        """Print a comprehensive performance report"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE TEST RESULTS")
        print("="*60)
        
        # Load Test Results
        print("\n🔗 LOAD TEST RESULTS:")
        print(f"  Total Connections: {load_test_results.get('total_connections', 0)}")
        print(f"  Successful: {load_test_results.get('successful_connections', 0)}")
        print(f"  Failed: {load_test_results.get('failed_connections', 0)}")
        print(f"  Success Rate: {load_test_results.get('success_rate', 0):.1f}%")
        
        if 'avg_response_time' in load_test_results:
            print(f"  Average Response Time: {load_test_results['avg_response_time']:.2f}s")
            print(f"  Min Response Time: {load_test_results['min_response_time']:.2f}s")
            print(f"  Max Response Time: {load_test_results['max_response_time']:.2f}s")
            print(f"  Std Dev: {load_test_results['std_dev_response_time']:.2f}s")
            print(f"  Avg Responses/Connection: {load_test_results['avg_responses_per_connection']:.1f}")
        
        # Benchmark Results
        print("\n🔬 INDIVIDUAL OPERATION BENCHMARKS:")
        
        if "stt" in benchmark_results:
            stt = benchmark_results["stt"]
            if stt["success"]:
                print(f"  STT: {stt['time']:.2f}s")
            else:
                print(f"  STT: FAILED - {stt.get('error', 'Unknown error')}")
        
        if "translation" in benchmark_results:
            trans = benchmark_results["translation"]
            if trans["success"]:
                print(f"  Translation (U→E): {trans['urdu_to_english_time']:.2f}s")
                print(f"  Translation (E→U): {trans['english_to_urdu_time']:.2f}s")
            else:
                print(f"  Translation: FAILED - {trans.get('error', 'Unknown error')}")
        
        if "tts" in benchmark_results:
            tts = benchmark_results["tts"]
            if tts["success"]:
                print(f"  TTS: {tts['time']:.2f}s ({tts['audio_size_bytes']} bytes)")
            else:
                print(f"  TTS: FAILED - {tts.get('error', 'Unknown error')}")
        
        # Performance Recommendations
        print("\n💡 PERFORMANCE RECOMMENDATIONS:")
        
        if 'avg_response_time' in load_test_results:
            avg_time = load_test_results['avg_response_time']
            if avg_time > 5.0:
                print("  ⚠️  Response time is high (>5s). Consider:")
                print("     - Implementing more aggressive caching")
                print("     - Using faster API endpoints")
                print("     - Optimizing audio processing")
            elif avg_time > 3.0:
                print("  ⚠️  Response time is moderate (3-5s). Consider:")
                print("     - Parallel processing optimizations")
                print("     - Connection pooling improvements")
            else:
                print("  ✅ Response time is good (<3s)")
        
        if load_test_results.get('success_rate', 0) < 95:
            print("  ⚠️  Success rate is below 95%. Check:")
            print("     - Network connectivity")
            print("     - API rate limits")
            print("     - Error handling")
        else:
            print("  ✅ Success rate is excellent (>95%)")
        
        print("\n" + "="*60)

async def main():
    """Main performance testing function"""
    tester = PerformanceTester()
    
    print("🚀 AI Tutor Backend Performance Testing")
    print("="*50)
    
    # Run individual operation benchmarks
    print("\n1. Benchmarking individual operations...")
    benchmark_results = await tester.benchmark_individual_operations()
    
    # Run load tests
    print("\n2. Running load tests...")
    
    # Test with 5 concurrent connections
    load_test_results = await tester.run_load_test(num_connections=5, concurrent=True)
    
    # Print comprehensive report
    tester.print_performance_report(load_test_results, benchmark_results)

if __name__ == "__main__":
    asyncio.run(main()) 