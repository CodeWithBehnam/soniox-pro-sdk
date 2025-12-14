# Performance and Load Testing Implementation Plan
## Soniox Pro SDK

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Proposal for Implementation

---

## Executive Summary

This document outlines a comprehensive performance and load testing strategy for the Soniox Pro SDK. It provides specific, actionable implementations for:
- Concurrent request handling
- Large file processing
- WebSocket streaming performance
- Connection pool efficiency
- Rate limiting behaviour
- Error recovery under load

---

## 1. Performance Testing Architecture

### 1.1 Testing Layers

```
┌─────────────────────────────────────────────┐
│        Performance Testing Pyramid          │
├─────────────────────────────────────────────┤
│  Chaos Tests (Network failures, etc.)       │ <- Low frequency
├─────────────────────────────────────────────┤
│  Load Tests (Locust, sustained load)        │ <- Weekly
├─────────────────────────────────────────────┤
│  Stress Tests (Breaking points)             │ <- Daily in CI
├─────────────────────────────────────────────┤
│  Integration Performance (End-to-end flows) │ <- Every PR
├─────────────────────────────────────────────┤
│  Microbenchmarks (pytest-benchmark)         │ <- Every commit
└─────────────────────────────────────────────┘
```

### 1.2 Test Environment Setup

```python
# tests/performance/conftest.py
"""
Performance testing fixtures and configuration.
"""
import pytest
import time
from typing import Generator
from unittest.mock import Mock, patch
import httpx
from soniox import SonioxClient
from tests.utils.mock_server import MockSonioxServer

@pytest.fixture(scope="session")
def performance_config():
    """Performance test configuration."""
    return {
        "api_key": "perf-test-key-12345",
        "api_base_url": "http://localhost:8888",
        "max_connections": 100,
        "max_keepalive_connections": 20,
        "timeout": 30.0,
    }

@pytest.fixture(scope="session")
def mock_server():
    """Start mock Soniox API server for performance tests."""
    server = MockSonioxServer(port=8888)
    server.start()
    yield server
    server.stop()

@pytest.fixture
def perf_client(performance_config, mock_server) -> Generator[SonioxClient, None, None]:
    """Create client for performance testing."""
    client = SonioxClient(**performance_config)
    yield client
    client.close()

@pytest.fixture
def metrics_collector():
    """Collect performance metrics during tests."""
    class MetricsCollector:
        def __init__(self):
            self.metrics = []

        def record(self, metric_name: str, value: float, unit: str = "ms"):
            self.metrics.append({
                "name": metric_name,
                "value": value,
                "unit": unit,
                "timestamp": time.time()
            })

        def get_stats(self, metric_name: str) -> dict:
            values = [m["value"] for m in self.metrics if m["name"] == metric_name]
            if not values:
                return {}

            values.sort()
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "p50": values[len(values) // 2],
                "p95": values[int(len(values) * 0.95)],
                "p99": values[int(len(values) * 0.99)],
            }

    return MetricsCollector()
```

---

## 2. Microbenchmark Tests (pytest-benchmark)

### 2.1 Client Initialisation Performance

```python
# tests/performance/test_client_init_benchmark.py
"""
Benchmark client initialisation and configuration.
"""
import pytest
from soniox import SonioxClient
from soniox.config import SonioxConfig

class TestClientInitBenchmarks:
    """Benchmarks for client initialisation."""

    @pytest.mark.benchmark(group="client-init")
    def test_client_init_with_defaults(self, benchmark):
        """Benchmark: Client initialisation with default config."""
        def create_client():
            client = SonioxClient(api_key="test-key")
            client.close()

        benchmark(create_client)
        # Target: <10ms

    @pytest.mark.benchmark(group="client-init")
    def test_client_init_with_custom_config(self, benchmark):
        """Benchmark: Client initialisation with custom config."""
        def create_client():
            config = SonioxConfig(
                api_key="test-key",
                max_connections=200,
                timeout=60.0,
            )
            client = SonioxClient(config=config)
            client.close()

        benchmark(create_client)
        # Target: <15ms

    @pytest.mark.benchmark(group="client-init")
    def test_config_validation(self, benchmark):
        """Benchmark: Configuration validation."""
        config = SonioxConfig(api_key="test-key")

        def validate():
            config.validate()

        benchmark(validate)
        # Target: <1ms
```

### 2.2 Connection Pool Performance

```python
# tests/performance/test_connection_pool_benchmark.py
"""
Benchmark connection pool efficiency and reuse.
"""
import pytest
from unittest.mock import Mock, patch
import httpx

class TestConnectionPoolBenchmarks:
    """Benchmarks for HTTP connection pooling."""

    @pytest.mark.benchmark(group="connection-pool")
    def test_connection_reuse(self, benchmark, perf_client, mock_server):
        """Benchmark: Connection reuse from pool."""
        # Warm up the pool
        for _ in range(5):
            perf_client.models.list()

        def make_requests():
            # Make 100 requests - should reuse connections
            for _ in range(100):
                perf_client.models.list()

        benchmark(make_requests)

        # Verify connection reuse
        stats = mock_server.get_connection_stats()
        assert stats["unique_connections"] < 25  # Should reuse, not create 100

    @pytest.mark.benchmark(group="connection-pool")
    def test_concurrent_connection_acquisition(self, benchmark, performance_config):
        """Benchmark: Concurrent connection acquisition from pool."""
        import concurrent.futures
        from soniox import SonioxClient

        def concurrent_requests():
            client = SonioxClient(**performance_config)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(client.models.list) for _ in range(100)]
                results = [f.result() for f in futures]
            client.close()
            return results

        result = benchmark(concurrent_requests)
        assert len(result) == 100
        # Target: <2s for 100 concurrent requests

    @pytest.mark.benchmark(group="connection-pool")
    def test_keepalive_efficiency(self, benchmark, perf_client):
        """Benchmark: Keep-alive connection efficiency."""
        def sequential_requests():
            # Requests should reuse same connection via keep-alive
            for _ in range(50):
                perf_client.models.list()
                time.sleep(0.1)  # Small delay between requests

        benchmark(sequential_requests)
        # Target: <6s (50 requests * 100ms + overhead)
```

### 2.3 Retry Logic Performance

```python
# tests/performance/test_retry_benchmark.py
"""
Benchmark retry logic and exponential backoff.
"""
import pytest
from soniox.utils import exponential_backoff, poll_until_complete

class TestRetryBenchmarks:
    """Benchmarks for retry and backoff logic."""

    @pytest.mark.benchmark(group="retry")
    def test_exponential_backoff_calculation(self, benchmark):
        """Benchmark: Exponential backoff calculation."""
        def calculate_backoffs():
            delays = [exponential_backoff(i) for i in range(10)]
            return delays

        result = benchmark(calculate_backoffs)
        assert len(result) == 10
        # Target: <1ms for 10 calculations

    @pytest.mark.benchmark(group="retry")
    def test_polling_success_fast(self, benchmark):
        """Benchmark: Fast polling success (completes immediately)."""
        call_count = {"value": 0}

        def get_status():
            call_count["value"] += 1
            return {"status": "completed"}

        def is_complete(status):
            return status["status"] == "completed"

        def is_failed(status):
            return False

        def get_error(status):
            return None

        def poll():
            return poll_until_complete(
                get_status,
                is_complete,
                is_failed,
                get_error,
                poll_interval=0.1
            )

        benchmark(poll)
        assert call_count["value"] == 1
        # Target: <5ms
```

---

## 3. Concurrent Request Testing

### 3.1 Concurrent Transcription Requests

```python
# tests/performance/test_concurrent_requests.py
"""
Test concurrent API request handling.
"""
import pytest
import concurrent.futures
import time
from soniox import SonioxClient

class TestConcurrentRequests:
    """Test concurrent request scenarios."""

    @pytest.mark.parametrize("concurrency", [10, 50, 100])
    @pytest.mark.timeout(60)
    def test_concurrent_transcription_creation(
        self,
        concurrency,
        perf_client,
        metrics_collector
    ):
        """Test creating multiple transcriptions concurrently."""
        # Upload test files first
        file_ids = []
        for i in range(concurrency):
            file = perf_client.files.upload(f"tests/fixtures/audio/test_{i % 5}.mp3")
            file_ids.append(file.id)

        # Create transcriptions concurrently
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(
                    perf_client.transcriptions.create,
                    file_id=file_id
                )
                for file_id in file_ids
            ]

            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Request failed: {e}")

        duration = time.time() - start_time

        # Metrics
        metrics_collector.record(f"concurrent_{concurrency}_duration", duration * 1000)
        throughput = concurrency / duration

        # Assertions
        assert len(results) == concurrency, "All requests should succeed"
        assert duration < 30, f"Should complete in <30s for {concurrency} requests"

        print(f"\nConcurrency: {concurrency}")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s")

        # Performance targets
        if concurrency == 10:
            assert duration < 5  # 10 requests in <5s
        elif concurrency == 50:
            assert duration < 15  # 50 requests in <15s
        elif concurrency == 100:
            assert duration < 30  # 100 requests in <30s

    @pytest.mark.parametrize("concurrency", [10, 50, 100, 200])
    def test_concurrent_file_listing(self, concurrency, perf_client, metrics_collector):
        """Test concurrent file listing operations."""
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(perf_client.files.list, limit=50)
                for _ in range(concurrency)
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start_time
        throughput = concurrency / duration

        # Metrics
        metrics_collector.record(f"list_concurrent_{concurrency}", duration * 1000)

        # Assertions
        assert len(results) == concurrency
        assert all(r.files is not None for r in results)

        print(f"\nList Concurrency: {concurrency}")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {throughput:.2f} req/s")

        # Should handle at least 20 req/s
        assert throughput > 20

    @pytest.mark.stress
    def test_connection_pool_exhaustion(self, performance_config):
        """Test behaviour when connection pool is exhausted."""
        # Create client with small pool
        config = performance_config.copy()
        config["max_connections"] = 5
        config["max_keepalive_connections"] = 2

        client = SonioxClient(**config)

        # Send more concurrent requests than pool size
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(client.models.list)
                for _ in range(20)
            ]

            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception as e:
                    results.append(e)

        client.close()

        # Should handle gracefully (queue requests)
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0, "Some requests should succeed"

        print(f"\nPool exhaustion test:")
        print(f"Successful: {len(successful)}/20")
        print(f"Failed: {20 - len(successful)}/20")
```

---

## 4. Large File Performance Testing

### 4.1 File Upload Performance

```python
# tests/performance/test_large_file_performance.py
"""
Test performance with large audio files.
"""
import pytest
import time
import os
from pathlib import Path
from tests.utils.generators import generate_test_audio_file

class TestLargeFilePerformance:
    """Performance tests for large file handling."""

    @pytest.mark.parametrize("file_size_mb", [1, 10, 50, 100])
    @pytest.mark.timeout(600)  # 10 minute timeout
    def test_file_upload_performance(
        self,
        file_size_mb,
        perf_client,
        metrics_collector,
        tmp_path
    ):
        """Test upload performance for files of varying sizes."""
        # Generate test file
        test_file = tmp_path / f"audio_{file_size_mb}mb.mp3"
        generate_test_audio_file(test_file, size_mb=file_size_mb)

        # Measure upload
        start_time = time.time()
        file = perf_client.files.upload(str(test_file))
        duration = time.time() - start_time

        # Calculate throughput
        throughput_mbps = (file_size_mb * 8) / duration  # Megabits per second

        # Metrics
        metrics_collector.record(f"upload_{file_size_mb}mb_duration", duration * 1000)
        metrics_collector.record(f"upload_{file_size_mb}mb_throughput", throughput_mbps, "Mbps")

        # Assertions
        assert file.id is not None, "Upload should succeed"

        print(f"\nFile size: {file_size_mb}MB")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {throughput_mbps:.2f} Mbps")

        # Performance targets (assuming 10 Mbps minimum)
        if file_size_mb == 1:
            assert duration < 5  # 1MB in <5s
        elif file_size_mb == 10:
            assert duration < 30  # 10MB in <30s
        elif file_size_mb == 50:
            assert duration < 120  # 50MB in <2min
        elif file_size_mb == 100:
            assert duration < 300  # 100MB in <5min

    @pytest.mark.stress
    @pytest.mark.parametrize("file_size_mb", [200, 500])
    @pytest.mark.timeout(1800)  # 30 minute timeout
    def test_extra_large_file_upload(
        self,
        file_size_mb,
        perf_client,
        tmp_path
    ):
        """Stress test: Upload extra large files."""
        test_file = tmp_path / f"audio_{file_size_mb}mb.mp3"
        generate_test_audio_file(test_file, size_mb=file_size_mb)

        start_time = time.time()
        file = perf_client.files.upload(str(test_file))
        duration = time.time() - start_time

        # Should complete without timeout
        assert file.id is not None
        assert duration < 1800  # 30 minutes max

        print(f"\nExtra large file: {file_size_mb}MB")
        print(f"Duration: {duration:.2f}s ({duration/60:.2f}min)")

    @pytest.mark.performance
    def test_concurrent_file_uploads(self, perf_client, tmp_path):
        """Test uploading multiple files concurrently."""
        # Generate 10 test files (10MB each)
        test_files = []
        for i in range(10):
            file_path = tmp_path / f"audio_{i}.mp3"
            generate_test_audio_file(file_path, size_mb=10)
            test_files.append(file_path)

        # Upload concurrently
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(perf_client.files.upload, str(f))
                for f in test_files
            ]

            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        duration = time.time() - start_time

        # Assertions
        assert len(results) == 10
        assert all(r.id is not None for r in results)

        print(f"\nConcurrent uploads (10 files @ 10MB each)")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {100/duration:.2f} MB/s")

        # Should complete in reasonable time
        assert duration < 60  # 100MB in <60s with 5 concurrent uploads
```

### 4.2 Memory Usage Testing

```python
# tests/performance/test_memory_usage.py
"""
Test memory usage under various loads.
"""
import pytest
import tracemalloc
import gc

class TestMemoryUsage:
    """Memory usage and leak detection tests."""

    @pytest.mark.performance
    def test_client_memory_footprint(self, performance_config):
        """Measure client memory footprint."""
        gc.collect()
        tracemalloc.start()

        # Create client
        snapshot_before = tracemalloc.take_snapshot()
        client = SonioxClient(**performance_config)
        snapshot_after = tracemalloc.take_snapshot()

        # Calculate memory usage
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
        total_memory_kb = sum(stat.size for stat in top_stats) / 1024

        client.close()
        tracemalloc.stop()

        print(f"\nClient memory footprint: {total_memory_kb:.2f} KB")

        # Should use <5MB for initialisation
        assert total_memory_kb < 5000

    @pytest.mark.stress
    def test_memory_leak_multiple_requests(self, perf_client):
        """Test for memory leaks during repeated requests."""
        gc.collect()
        tracemalloc.start()

        # Make many requests
        snapshot_before = tracemalloc.take_snapshot()

        for _ in range(1000):
            perf_client.models.list()

        snapshot_after = tracemalloc.take_snapshot()

        # Check memory growth
        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
        total_growth_mb = sum(stat.size for stat in top_stats) / (1024 * 1024)

        tracemalloc.stop()

        print(f"\nMemory growth after 1000 requests: {total_growth_mb:.2f} MB")

        # Should not grow significantly (<50MB for 1000 requests)
        assert total_growth_mb < 50

    @pytest.mark.stress
    def test_large_file_memory_usage(self, perf_client, tmp_path):
        """Test memory usage when handling large files."""
        # Generate 100MB file
        test_file = tmp_path / "large_audio.mp3"
        generate_test_audio_file(test_file, size_mb=100)

        gc.collect()
        tracemalloc.start()

        snapshot_before = tracemalloc.take_snapshot()

        # Upload large file
        file = perf_client.files.upload(str(test_file))

        snapshot_after = tracemalloc.take_snapshot()

        top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
        peak_memory_mb = max(stat.size for stat in top_stats) / (1024 * 1024)

        tracemalloc.stop()

        print(f"\nPeak memory for 100MB upload: {peak_memory_mb:.2f} MB")

        # Should stream file, not load entirely into memory
        # Peak usage should be <200MB (not 100MB+ all in memory)
        assert peak_memory_mb < 200
```

---

## 5. WebSocket Streaming Performance

### 5.1 Real-Time Streaming Latency

```python
# tests/performance/test_websocket_performance.py
"""
Test WebSocket streaming performance and latency.
"""
import pytest
import time
from soniox import SonioxRealtimeClient

class TestWebSocketPerformance:
    """Performance tests for WebSocket streaming."""

    @pytest.mark.parametrize("chunk_size_kb", [1, 4, 16, 64])
    @pytest.mark.timeout(120)
    def test_streaming_latency(
        self,
        chunk_size_kb,
        mock_websocket_server,
        metrics_collector
    ):
        """Test latency for different audio chunk sizes."""
        client = SonioxRealtimeClient(
            api_key="test-key",
            model="stt-rt-v3"
        )

        latencies = []

        with client.stream() as stream:
            # Send 100 audio chunks
            for i in range(100):
                chunk = generate_audio_chunk(chunk_size_kb * 1024)

                send_time = time.time()
                stream.send_audio(chunk)

                # Wait for response
                for response in stream:
                    if response.tokens:
                        receive_time = time.time()
                        latency_ms = (receive_time - send_time) * 1000
                        latencies.append(latency_ms)
                        break

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        latencies.sort()
        p95_latency = latencies[int(len(latencies) * 0.95)]
        p99_latency = latencies[int(len(latencies) * 0.99)]

        metrics_collector.record(f"ws_latency_{chunk_size_kb}kb_avg", avg_latency)
        metrics_collector.record(f"ws_latency_{chunk_size_kb}kb_p95", p95_latency)

        print(f"\nChunk size: {chunk_size_kb}KB")
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"P95 latency: {p95_latency:.2f}ms")
        print(f"P99 latency: {p99_latency:.2f}ms")

        # Performance targets
        assert avg_latency < 100, "Average latency should be <100ms"
        assert p95_latency < 200, "P95 latency should be <200ms"

    @pytest.mark.parametrize("duration_seconds", [10, 60, 300])
    @pytest.mark.timeout(400)
    def test_long_duration_streaming(
        self,
        duration_seconds,
        mock_websocket_server
    ):
        """Test streaming stability over longer durations."""
        client = SonioxRealtimeClient(api_key="test-key")

        token_count = 0
        errors = []
        start_time = time.time()

        with client.stream() as stream:
            # Stream for specified duration
            while time.time() - start_time < duration_seconds:
                # Send audio chunk every 100ms
                chunk = generate_audio_chunk(4096)  # 4KB chunks
                try:
                    stream.send_audio(chunk)
                except Exception as e:
                    errors.append(e)

                # Collect tokens
                for response in stream:
                    token_count += len(response.tokens)
                    if response.error_code:
                        errors.append(response.error_message)

                time.sleep(0.1)

        duration = time.time() - start_time

        print(f"\nStreaming duration: {duration:.2f}s")
        print(f"Tokens received: {token_count}")
        print(f"Errors: {len(errors)}")

        # Assertions
        assert len(errors) == 0, "Should have no errors during streaming"
        assert token_count > 0, "Should receive tokens"

    @pytest.mark.stress
    def test_concurrent_websocket_connections(self, mock_websocket_server):
        """Test multiple concurrent WebSocket connections."""
        num_connections = 10

        def stream_audio(client_id):
            """Stream audio on a single connection."""
            client = SonioxRealtimeClient(api_key="test-key")
            tokens = []

            with client.stream() as stream:
                for _ in range(50):
                    chunk = generate_audio_chunk(4096)
                    stream.send_audio(chunk)

                for response in stream:
                    tokens.extend(response.tokens)

            return len(tokens)

        # Run concurrent streams
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
            futures = [
                executor.submit(stream_audio, i)
                for i in range(num_connections)
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start_time

        print(f"\nConcurrent WebSocket connections: {num_connections}")
        print(f"Duration: {duration:.2f}s")
        print(f"Total tokens: {sum(results)}")

        # Assertions
        assert all(r > 0 for r in results), "All streams should receive tokens"
        assert duration < 60, "Should complete in <60s"
```

---

## 6. Load Testing with Locust

### 6.1 Locust Test Suite

```python
# tests/load/locustfile.py
"""
Load testing suite using Locust.
"""
from locust import HttpUser, task, between, events
import time
import random

class SonioxAPIUser(HttpUser):
    """Simulated user for Soniox API load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "https://api.soniox.com"

    def on_start(self):
        """Set up authentication on user start."""
        self.client.headers["Authorization"] = f"Bearer {API_KEY}"
        self.file_ids = []

    @task(3)
    def list_files(self):
        """Task: List uploaded files."""
        with self.client.get(
            "/api/v1/files",
            params={"limit": 50},
            name="/files [list]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.file_ids = [f["id"] for f in data.get("files", [])]
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def create_transcription(self):
        """Task: Create transcription."""
        if not self.file_ids:
            return

        file_id = random.choice(self.file_ids)

        with self.client.post(
            "/api/v1/transcriptions",
            json={
                "model": "stt-async-v3",
                "file_id": file_id,
                "enable_speaker_diarization": True
            },
            name="/transcriptions [create]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)
    def get_models(self):
        """Task: Get available models."""
        with self.client.get(
            "/api/v1/models",
            name="/models [list]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

# Event handlers for metrics collection
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Collect request metrics."""
    if exception:
        print(f"Request failed: {name} - {exception}")
```

### 6.2 Load Test Scenarios

```bash
# Scenario 1: Baseline load (10 users)
locust -f tests/load/locustfile.py \
  --users 10 \
  --spawn-rate 1 \
  --run-time 10m \
  --html reports/baseline_load.html

# Scenario 2: Normal load (50 users)
locust -f tests/load/locustfile.py \
  --users 50 \
  --spawn-rate 5 \
  --run-time 30m \
  --html reports/normal_load.html

# Scenario 3: Peak load (100 users)
locust -f tests/load/locustfile.py \
  --users 100 \
  --spawn-rate 10 \
  --run-time 30m \
  --html reports/peak_load.html

# Scenario 4: Stress test (500 users)
locust -f tests/load/locustfile.py \
  --users 500 \
  --spawn-rate 25 \
  --run-time 15m \
  --html reports/stress_test.html
```

---

## 7. Performance Monitoring and Reporting

### 7.1 Custom Performance Reporter

```python
# tests/performance/reporter.py
"""
Performance test results reporter.
"""
import json
from pathlib import Path
from datetime import datetime

class PerformanceReporter:
    """Generate performance test reports."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []

    def add_result(
        self,
        test_name: str,
        metrics: dict,
        status: str = "PASS"
    ):
        """Add test result."""
        self.results.append({
            "test": test_name,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "metrics": metrics
        })

    def generate_report(self):
        """Generate HTML performance report."""
        report_file = self.output_dir / f"performance_report_{datetime.now():%Y%m%d_%H%M%S}.html"

        html = self._generate_html()

        with open(report_file, "w") as f:
            f.write(html)

        # Also save JSON
        json_file = report_file.with_suffix(".json")
        with open(json_file, "w") as f:
            json.dump(self.results, f, indent=2)

        return report_file

    def _generate_html(self) -> str:
        """Generate HTML report content."""
        # Implementation of HTML generation
        pass
```

### 7.2 CI/CD Integration

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run performance benchmarks
        run: |
          uv run pytest tests/performance/ \
            --benchmark-only \
            --benchmark-json=benchmark.json \
            --benchmark-min-rounds=10

      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
          alert-threshold: '150%'
          comment-on-alert: true
          fail-on-alert: false

      - name: Upload performance report
        uses: actions/upload-artifact@v4
        with:
          name: performance-report
          path: benchmark.json
```

---

## 8. Performance Baselines and Targets

### 8.1 Target Performance Metrics

| Operation | Target (p50) | Target (p95) | Target (p99) |
|-----------|--------------|--------------|--------------|
| Client init | <10ms | <20ms | <50ms |
| File list | <200ms | <500ms | <1s |
| File upload (10MB) | <5s | <10s | <20s |
| File upload (100MB) | <60s | <120s | <180s |
| Transcription create | <500ms | <1s | <2s |
| WebSocket latency | <50ms | <100ms | <200ms |
| Concurrent requests (100) | <10s | <20s | <30s |

### 8.2 Resource Usage Targets

| Resource | Target | Max Acceptable |
|----------|--------|----------------|
| Memory (client init) | <5MB | <10MB |
| Memory (100 concurrent) | <100MB | <200MB |
| Memory (large file upload) | <150MB | <300MB |
| Connection pool efficiency | >90% | >80% |
| Request success rate | >99.9% | >99% |

---

## 9. Implementation Timeline

### Week 1: Foundation
- Set up pytest-benchmark
- Create performance test infrastructure
- Implement basic microbenchmarks
- Add performance fixtures

### Week 2: Core Tests
- Implement concurrent request tests
- Add large file performance tests
- Create memory usage tests
- Set up metrics collection

### Week 3: Advanced Tests
- Implement WebSocket performance tests
- Add stress test scenarios
- Create load testing suite (Locust)
- Set up performance reporting

### Week 4: Integration
- Integrate with CI/CD
- Set up performance regression tracking
- Create performance dashboards
- Document performance baselines

---

## 10. Conclusion

This performance testing plan provides a comprehensive framework for ensuring the Soniox Pro SDK meets production-grade performance standards. Key deliverables include:

- **Microbenchmarks** for fast feedback on code changes
- **Stress tests** for identifying breaking points
- **Load tests** for validating real-world usage patterns
- **Continuous monitoring** for preventing performance regressions

**Estimated Effort:** 120 hours across 4 weeks

**Expected Outcomes:**
- 20+ performance tests
- Automated performance regression detection
- Clear performance baselines
- Production-ready performance validation
