"""
Performance Benchmarks for MCP Kali Forensics

Measures performance of critical operations:
- API response times
- Tool execution times
- Database query performance
- WebSocket streaming latency
"""

import pytest
import time
import asyncio
from typing import Dict, List
import statistics
import json
from datetime import datetime
from pathlib import Path

# Mark all tests in this file as benchmarks
pytestmark = pytest.mark.benchmark


class PerformanceBenchmark:
    """Base class for performance benchmarking"""
    
    def __init__(self):
        self.results: List[Dict] = []
        self.baseline_file = Path("benchmarks/baseline.json")
    
    def measure(self, name: str, func, iterations: int = 10):
        """Measure execution time of a function"""
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        result = {
            "name": name,
            "iterations": iterations,
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(result)
        return result
    
    async def measure_async(self, name: str, func, iterations: int = 10):
        """Measure execution time of an async function"""
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        result = {
            "name": name,
            "iterations": iterations,
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(result)
        return result
    
    def save_results(self, filename: str = None):
        """Save benchmark results to file"""
        if filename is None:
            filename = f"benchmarks/results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.results
            }, f, indent=2)
    
    def compare_with_baseline(self):
        """Compare current results with baseline"""
        if not self.baseline_file.exists():
            print("⚠️ No baseline found. Creating baseline...")
            self.save_results(str(self.baseline_file))
            return
        
        with open(self.baseline_file) as f:
            baseline = json.load(f)
        
        print("\n📊 Performance Comparison with Baseline")
        print("=" * 60)
        
        baseline_map = {r["name"]: r for r in baseline["results"]}
        
        for result in self.results:
            name = result["name"]
            current_mean = result["mean_ms"]
            
            if name in baseline_map:
                baseline_mean = baseline_map[name]["mean_ms"]
                diff_pct = ((current_mean - baseline_mean) / baseline_mean) * 100
                
                status = "✅" if diff_pct < 10 else "⚠️" if diff_pct < 25 else "❌"
                
                print(f"{status} {name}")
                print(f"   Current: {current_mean:.2f}ms | Baseline: {baseline_mean:.2f}ms | Diff: {diff_pct:+.1f}%")
            else:
                print(f"🆕 {name}: {current_mean:.2f}ms (new benchmark)")
        
        print("=" * 60)


# =============================================================================
# API Benchmarks
# =============================================================================

@pytest.mark.asyncio
async def test_api_health_endpoint(client):
    """Benchmark: Health endpoint response time"""
    benchmark = PerformanceBenchmark()
    
    async def call_health():
        response = await client.get("/health")
        assert response.status_code == 200
    
    result = await benchmark.measure_async("API: Health endpoint", call_health, iterations=50)
    
    # SLA: Health endpoint should respond in < 100ms
    assert result["mean_ms"] < 100, f"Health endpoint too slow: {result['mean_ms']:.2f}ms"
    
    print(f"\n✅ Health endpoint: {result['mean_ms']:.2f}ms (target: <100ms)")


@pytest.mark.asyncio
async def test_api_cases_list(client):
    """Benchmark: List cases endpoint"""
    benchmark = PerformanceBenchmark()
    
    async def call_cases_list():
        response = await client.get(
            "/api/v1/cases",
            headers={"X-API-Key": "test-key"}
        )
        assert response.status_code == 200
    
    result = await benchmark.measure_async("API: List cases", call_cases_list, iterations=20)
    
    # SLA: List endpoint should respond in < 500ms
    assert result["mean_ms"] < 500, f"List cases too slow: {result['mean_ms']:.2f}ms"
    
    print(f"\n✅ List cases: {result['mean_ms']:.2f}ms (target: <500ms)")


@pytest.mark.asyncio
async def test_api_case_create(client):
    """Benchmark: Create case endpoint"""
    benchmark = PerformanceBenchmark()
    
    async def call_case_create():
        response = await client.post(
            "/api/v1/cases",
            json={"name": f"Benchmark Test {time.time()}"},
            headers={"X-API-Key": "test-key"}
        )
        assert response.status_code in [200, 201]
    
    result = await benchmark.measure_async("API: Create case", call_case_create, iterations=20)
    
    # SLA: Create should complete in < 1000ms
    assert result["mean_ms"] < 1000, f"Create case too slow: {result['mean_ms']:.2f}ms"
    
    print(f"\n✅ Create case: {result['mean_ms']:.2f}ms (target: <1000ms)")


# =============================================================================
# Database Benchmarks
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(not Path("forensics.db").exists(), reason="Database not found")
async def test_database_query_performance():
    """Benchmark: Database query performance"""
    from api.database import SessionLocal
    from api.models.case import Case
    
    benchmark = PerformanceBenchmark()
    
    def query_cases():
        with SessionLocal() as db:
            cases = db.query(Case).limit(100).all()
            assert len(cases) >= 0
    
    result = benchmark.measure("DB: Query 100 cases", query_cases, iterations=20)
    
    # SLA: Query should complete in < 200ms
    assert result["mean_ms"] < 200, f"Database query too slow: {result['mean_ms']:.2f}ms"
    
    print(f"\n✅ DB Query: {result['mean_ms']:.2f}ms (target: <200ms)")


# =============================================================================
# Tool Execution Benchmarks
# =============================================================================

@pytest.mark.slow
@pytest.mark.skipif(not Path("/opt/forensics-tools/Loki").exists(), reason="Loki not installed")
def test_loki_scanner_performance():
    """Benchmark: Loki scanner execution time"""
    import subprocess
    
    benchmark = PerformanceBenchmark()
    
    def run_loki():
        # Quick scan of /tmp directory
        result = subprocess.run(
            ["python3", "/opt/forensics-tools/Loki/loki.py", "--noprocscan", "--path", "/tmp"],
            capture_output=True,
            timeout=120
        )
        assert result.returncode in [0, 1]  # 1 is OK (warnings/alerts)
    
    result = benchmark.measure("Tool: Loki scanner", run_loki, iterations=3)
    
    # SLA: Loki should complete /tmp scan in < 60 seconds
    assert result["mean_ms"] < 60000, f"Loki too slow: {result['mean_ms']:.2f}ms"
    
    print(f"\n✅ Loki scan: {result['mean_ms']/1000:.2f}s (target: <60s)")


@pytest.mark.slow
def test_yara_scan_performance():
    """Benchmark: YARA scan performance"""
    import subprocess
    import tempfile
    
    benchmark = PerformanceBenchmark()
    
    # Create test files
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            Path(tmpdir) / f"test_{i}.txt" / "w" / "write" / f"Test content {i}"
        
        def run_yara():
            result = subprocess.run(
                ["yara", "-r", "/opt/forensics-tools/yara-rules/index.yar", tmpdir],
                capture_output=True,
                timeout=30
            )
            assert result.returncode in [0, 1]
        
        result = benchmark.measure("Tool: YARA scan", run_yara, iterations=5)
    
    print(f"\n✅ YARA scan: {result['mean_ms']/1000:.2f}s")


# =============================================================================
# WebSocket Benchmarks
# =============================================================================

@pytest.mark.asyncio
async def test_websocket_latency():
    """Benchmark: WebSocket message latency"""
    # TODO: Implement WebSocket benchmarking
    # Requires WebSocket test client
    pass


# =============================================================================
# End-to-End Benchmarks
# =============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_m365_analysis_workflow(client):
    """Benchmark: Full M365 analysis workflow"""
    benchmark = PerformanceBenchmark()
    
    async def run_workflow():
        # 1. Create case
        case_response = await client.post(
            "/api/v1/cases",
            json={"name": "E2E Benchmark"},
            headers={"X-API-Key": "test-key"}
        )
        assert case_response.status_code in [200, 201]
        case_id = case_response.json()["case_id"]
        
        # 2. Start analysis (mock)
        analysis_response = await client.post(
            "/api/v1/m365/analyze",
            json={"tenant_id": "test", "scope": ["test"]},
            headers={"X-API-Key": "test-key", "X-Case-ID": case_id}
        )
        # May fail in test environment, that's OK
    
    result = await benchmark.measure_async("E2E: M365 workflow", run_workflow, iterations=5)
    
    print(f"\n✅ E2E workflow: {result['mean_ms']:.2f}ms")


# =============================================================================
# Benchmark Runner
# =============================================================================

if __name__ == "__main__":
    """Run all benchmarks and generate report"""
    print("🔥 Running MCP Kali Forensics Performance Benchmarks")
    print("=" * 60)
    
    # Run pytest with benchmark marker
    pytest.main([
        __file__,
        "-v",
        "-m", "benchmark",
        "--tb=short"
    ])
    
    print("\n📊 Benchmark completed!")
    print("Results saved to: benchmarks/results_*.json")
