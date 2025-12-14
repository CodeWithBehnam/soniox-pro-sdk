# Soniox Pro SDK - Testing Recommendations and Action Plan

**Priority:** CRITICAL
**Status:** Immediate Action Required
**Estimated Effort:** 200 hours over 8 weeks

---

## Executive Summary

The Soniox Pro SDK has **critical gaps in test coverage (46.08%)** that pose significant production risks. This document provides actionable recommendations to achieve production-ready quality standards.

**Key Findings:**
- ❌ **WebSocket streaming completely untested** (19.44% coverage)
- ❌ **No performance or load testing**
- ❌ **HTTP client core logic untested** (33.74% coverage)
- ❌ **No integration tests**
- ❌ **No error recovery scenarios tested**
- ⚠️ **2 unit tests currently failing**

**Risk Level:** HIGH - Production deployment not recommended without addressing these gaps.

---

## Immediate Actions (This Week)

### 1. Fix Failing Tests
**Priority:** CRITICAL | **Effort:** 2 hours

```bash
# Issue: Tests fail due to .env API key loading
# Files affected:
# - tests/test_client.py::test_client_requires_api_key
# - tests/test_client.py::test_config_validation
```

**Solution:**
```python
# tests/conftest.py (CREATE THIS FILE)
import pytest
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch):
    """Isolate test environment from .env files."""
    # Clear all Soniox-related environment variables
    for key in ["SONIOX_API_KEY", "SONIOX_KEY", "API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    # Mock dotenv loading to prevent .env file reading
    with patch("soniox.config.load_dotenv"):
        yield
```

### 2. Set Up Test Infrastructure
**Priority:** CRITICAL | **Effort:** 8 hours

```bash
# Add required testing dependencies
uv add --dev pytest-benchmark pytest-timeout pytest-xdist
uv add --dev responses pytest-httpx  # HTTP mocking
uv add --dev locust  # Load testing
uv add --dev faker  # Test data generation
uv add --dev memory-profiler  # Memory profiling
```

**Create test structure:**
```
tests/
├── conftest.py              # ← CREATE: Shared fixtures
├── unit/                    # ← CREATE: Unit tests
│   ├── test_client.py
│   ├── test_realtime.py
│   ├── test_utils.py
│   └── test_errors.py
├── integration/             # ← CREATE: Integration tests
│   ├── test_file_flow.py
│   ├── test_transcription_flow.py
│   └── test_realtime_flow.py
├── performance/             # ← CREATE: Performance tests
│   ├── conftest.py
│   ├── test_benchmarks.py
│   ├── test_concurrent.py
│   └── test_large_files.py
├── load/                    # ← CREATE: Load tests
│   └── locustfile.py
└── utils/                   # ← CREATE: Test utilities
    ├── generators.py
    └── mock_server.py
```

### 3. Create Core Test Fixtures
**Priority:** CRITICAL | **Effort:** 4 hours

```python
# tests/conftest.py
import pytest
import responses
from pathlib import Path
from soniox import SonioxClient

@pytest.fixture
def test_api_key() -> str:
    """Standard test API key."""
    return "test-api-key-12345"

@pytest.fixture
def mock_soniox_api():
    """Mock Soniox API responses."""
    with responses.RequestsMock() as rsps:
        # Mock common endpoints
        rsps.add(
            responses.GET,
            "https://api.soniox.com/api/v1/models",
            json={"models": [{"id": "stt-async-v3", "name": "Async V3"}]},
            status=200
        )

        rsps.add(
            responses.POST,
            "https://api.soniox.com/api/v1/files",
            json={"file": {"id": "file-123", "name": "test.mp3"}},
            status=200
        )

        yield rsps

@pytest.fixture
def client(test_api_key, mock_soniox_api):
    """Create test client with mocked API."""
    with patch("soniox.config.load_dotenv"):
        client = SonioxClient(api_key=test_api_key)
        yield client
        client.close()

@pytest.fixture
def test_audio_file(tmp_path) -> Path:
    """Generate small test audio file."""
    from tests.utils.generators import generate_test_audio_file
    file_path = tmp_path / "test_audio.mp3"
    generate_test_audio_file(file_path, size_mb=1)
    return file_path
```

---

## Week 1: Critical Unit Tests

### Priority 1: HTTP Client Tests
**Target Coverage:** 90%+ for `client.py`

```python
# tests/unit/test_client_retry_logic.py
"""Test HTTP client retry logic."""
import pytest
import responses
from soniox import SonioxClient
from soniox.errors import SonioxTimeoutError, SonioxRateLimitError

class TestClientRetryLogic:
    """Test retry and backoff behaviour."""

    def test_retry_on_timeout(self, test_api_key):
        """Test automatic retry on timeout."""
        with responses.RequestsMock() as rsps:
            # First two attempts timeout, third succeeds
            rsps.add(responses.GET, "https://api.soniox.com/api/v1/models",
                     body=httpx.TimeoutException("Timeout"))
            rsps.add(responses.GET, "https://api.soniox.com/api/v1/models",
                     body=httpx.TimeoutException("Timeout"))
            rsps.add(responses.GET, "https://api.soniox.com/api/v1/models",
                     json={"models": []}, status=200)

            client = SonioxClient(api_key=test_api_key, max_retries=3)
            result = client.models.list()

            assert result is not None
            assert len(rsps.calls) == 3  # Verify retry attempts

    def test_retry_exhaustion_raises_error(self, test_api_key):
        """Test error raised when retries exhausted."""
        with responses.RequestsMock() as rsps:
            # All attempts timeout
            for _ in range(4):  # max_retries + 1
                rsps.add(responses.GET, "https://api.soniox.com/api/v1/models",
                         body=httpx.TimeoutException("Timeout"))

            client = SonioxClient(api_key=test_api_key, max_retries=3)

            with pytest.raises(SonioxTimeoutError):
                client.models.list()

    def test_rate_limit_with_retry_after(self, test_api_key):
        """Test rate limit handling with Retry-After header."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.soniox.com/api/v1/models",
                json={"error_message": "Rate limit exceeded"},
                status=429,
                headers={"Retry-After": "60"}
            )

            client = SonioxClient(api_key=test_api_key)

            with pytest.raises(SonioxRateLimitError) as exc_info:
                client.models.list()

            assert exc_info.value.retry_after == 60

    def test_exponential_backoff_timing(self, test_api_key, monkeypatch):
        """Test exponential backoff delay increases."""
        import time
        sleep_calls = []

        def mock_sleep(duration):
            sleep_calls.append(duration)

        monkeypatch.setattr(time, "sleep", mock_sleep)

        with responses.RequestsMock() as rsps:
            # First 3 attempts fail
            for _ in range(3):
                rsps.add(responses.GET, "https://api.soniox.com/api/v1/models",
                         body=httpx.TimeoutException("Timeout"))
            # Fourth succeeds
            rsps.add(responses.GET, "https://api.soniox.com/api/v1/models",
                     json={"models": []}, status=200)

            client = SonioxClient(api_key=test_api_key, max_retries=3)
            client.models.list()

        # Verify exponential increase
        assert len(sleep_calls) == 3
        assert sleep_calls[0] < sleep_calls[1] < sleep_calls[2]
```

### Priority 2: WebSocket Tests
**Target Coverage:** 90%+ for `realtime.py`

```python
# tests/unit/test_realtime_websocket.py
"""Test WebSocket streaming functionality."""
import pytest
from unittest.mock import Mock, MagicMock
from soniox import SonioxRealtimeClient
from soniox.errors import SonioxWebSocketError

class TestRealtimeWebSocket:
    """Test real-time WebSocket streaming."""

    def test_audio_send_success(self, mock_websocket):
        """Test successful audio chunk sending."""
        client = SonioxRealtimeClient(api_key="test-key")

        with client.stream() as stream:
            audio_data = b"fake_audio_data"
            stream.send_audio(audio_data)

            # Verify WebSocket send called
            mock_websocket.send.assert_called_once_with(audio_data)

    def test_audio_send_to_closed_stream_raises_error(self, mock_websocket):
        """Test sending to closed stream raises error."""
        client = SonioxRealtimeClient(api_key="test-key")

        stream = client.stream().__enter__()
        stream.close()

        with pytest.raises(SonioxWebSocketError, match="Stream is closed"):
            stream.send_audio(b"data")

    def test_websocket_server_error_response(self, mock_websocket):
        """Test handling of server error in response."""
        mock_websocket.__iter__ = Mock(return_value=iter([
            json.dumps({
                "error_code": "INVALID_AUDIO",
                "error_message": "Invalid audio format"
            })
        ]))

        client = SonioxRealtimeClient(api_key="test-key")

        with pytest.raises(SonioxWebSocketError, match="INVALID_AUDIO"):
            with client.stream() as stream:
                for response in stream:
                    pass

    def test_response_iteration_with_tokens(self, mock_websocket):
        """Test iterating through responses with tokens."""
        mock_responses = [
            json.dumps({"tokens": [{"text": "Hello", "is_final": False}]}),
            json.dumps({"tokens": [{"text": "World", "is_final": True}]}),
            json.dumps({"finished": True})
        ]
        mock_websocket.__iter__ = Mock(return_value=iter(mock_responses))

        client = SonioxRealtimeClient(api_key="test-key")
        all_tokens = []

        with client.stream() as stream:
            for response in stream:
                all_tokens.extend(response.tokens)

        assert len(all_tokens) == 2
        assert all_tokens[0].text == "Hello"
        assert all_tokens[1].text == "World"
```

### Priority 3: Utilities Tests
**Target Coverage:** 100% for `utils.py`

```python
# tests/unit/test_utils.py
"""Test utility functions."""
import pytest
import time
from soniox.utils import (
    exponential_backoff,
    extract_retry_after,
    poll_until_complete
)
from soniox.errors import SonioxTimeoutError

class TestUtilities:
    """Test utility functions."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff increases correctly."""
        delays = [exponential_backoff(i) for i in range(5)]

        # Should increase exponentially
        assert delays[0] < delays[1] < delays[2] < delays[3] < delays[4]

        # First delay should be base_delay
        assert delays[0] == 1.0

        # Should respect max_delay
        large_delay = exponential_backoff(100, max_delay=60.0)
        assert large_delay == 60.0

    def test_extract_retry_after_valid(self):
        """Test extracting valid Retry-After header."""
        headers = {"Retry-After": "120"}
        assert extract_retry_after(headers) == 120

        headers_lower = {"retry-after": "60"}
        assert extract_retry_after(headers_lower) == 60

    def test_extract_retry_after_missing(self):
        """Test extracting missing Retry-After header."""
        headers = {}
        assert extract_retry_after(headers) is None

    def test_extract_retry_after_invalid(self):
        """Test extracting invalid Retry-After value."""
        headers = {"Retry-After": "invalid"}
        assert extract_retry_after(headers) is None

    def test_poll_until_complete_immediate_success(self):
        """Test polling when operation completes immediately."""
        call_count = {"value": 0}

        def get_status():
            call_count["value"] += 1
            return {"status": "completed"}

        result = poll_until_complete(
            get_status=get_status,
            is_complete=lambda s: s["status"] == "completed",
            is_failed=lambda s: False,
            get_error=lambda s: None,
            poll_interval=0.1
        )

        assert result["status"] == "completed"
        assert call_count["value"] == 1

    def test_poll_until_complete_after_retries(self):
        """Test polling succeeds after several attempts."""
        call_count = {"value": 0}

        def get_status():
            call_count["value"] += 1
            if call_count["value"] < 3:
                return {"status": "processing"}
            return {"status": "completed"}

        start = time.time()
        result = poll_until_complete(
            get_status=get_status,
            is_complete=lambda s: s["status"] == "completed",
            is_failed=lambda s: False,
            get_error=lambda s: None,
            poll_interval=0.1
        )
        duration = time.time() - start

        assert result["status"] == "completed"
        assert call_count["value"] == 3
        assert duration >= 0.2  # At least 2 poll intervals

    def test_poll_until_complete_timeout(self):
        """Test polling raises timeout error."""
        def get_status():
            return {"status": "processing"}

        with pytest.raises(SonioxTimeoutError):
            poll_until_complete(
                get_status=get_status,
                is_complete=lambda s: False,
                is_failed=lambda s: False,
                get_error=lambda s: None,
                poll_interval=0.1,
                timeout=0.3
            )

    def test_poll_until_complete_failure(self):
        """Test polling raises error on operation failure."""
        def get_status():
            return {"status": "failed", "error": "Processing error"}

        with pytest.raises(Exception, match="Processing error"):
            poll_until_complete(
                get_status=get_status,
                is_complete=lambda s: False,
                is_failed=lambda s: s["status"] == "failed",
                get_error=lambda s: s.get("error"),
                poll_interval=0.1
            )
```

---

## Week 2-3: Integration & Performance Tests

### Integration Tests
**Effort:** 40 hours

```python
# tests/integration/test_transcription_flow.py
"""Integration test for complete transcription workflow."""
import pytest

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("SONIOX_API_KEY"), reason="Requires API key")
def test_complete_transcription_workflow(test_audio_file):
    """Test complete workflow: upload, transcribe, retrieve."""
    client = SonioxClient()  # Uses real API key

    # 1. Upload file
    file = client.files.upload(str(test_audio_file))
    assert file.id is not None

    # 2. Create transcription
    transcription = client.transcriptions.create(file_id=file.id)
    assert transcription.id is not None
    assert transcription.status in ["queued", "processing"]

    # 3. Wait for completion
    result = client.transcriptions.wait_for_completion(
        transcription.id,
        timeout=300  # 5 minutes
    )
    assert result.transcription.status == "completed"
    assert result.transcript is not None

    # 4. Cleanup
    client.transcriptions.delete(transcription.id)
    client.files.delete(file.id)
```

### Performance Benchmarks
**Effort:** 30 hours

```python
# tests/performance/test_benchmarks.py
"""Core performance benchmarks."""
import pytest

@pytest.mark.benchmark(group="init")
def test_client_init_benchmark(benchmark, test_api_key):
    """Benchmark client initialisation."""
    def create_client():
        client = SonioxClient(api_key=test_api_key)
        client.close()

    benchmark(create_client)
    # Target: <10ms

@pytest.mark.benchmark(group="requests")
def test_request_throughput(benchmark, client):
    """Benchmark request throughput."""
    def make_requests():
        for _ in range(100):
            client.models.list()

    benchmark(make_requests)
    # Target: <10s for 100 requests
```

---

## Week 4: Load Testing

### Locust Load Tests
**Effort:** 30 hours

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class SonioxUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_files(self):
        self.client.get("/api/v1/files")

    @task(2)
    def create_transcription(self):
        self.client.post("/api/v1/transcriptions", json={
            "model": "stt-async-v3",
            "file_id": "test-file-123"
        })
```

**Run load tests:**
```bash
# Baseline: 10 users
locust -f tests/load/locustfile.py --users 10 --spawn-rate 1 --run-time 10m

# Normal load: 50 users
locust -f tests/load/locustfile.py --users 50 --spawn-rate 5 --run-time 30m

# Peak load: 100 users
locust -f tests/load/locustfile.py --users 100 --spawn-rate 10 --run-time 30m
```

---

## CI/CD Integration

### Update GitHub Actions
**File:** `.github/workflows/test.yml`

```yaml
- name: Run tests with coverage
  run: |
    uv run pytest tests/ \
      --cov=soniox \
      --cov-report=xml \
      --cov-report=term \
      --cov-fail-under=80 \
      -v

- name: Run performance benchmarks
  run: |
    uv run pytest tests/performance/ \
      --benchmark-only \
      --benchmark-json=benchmark.json

- name: Check performance regression
  uses: benchmark-action/github-action-benchmark@v1
  with:
    tool: 'pytest'
    output-file-path: benchmark.json
    fail-on-alert: true
    alert-threshold: '150%'
```

---

## Success Metrics

### Coverage Targets
- **Overall:** 46.08% → 80% (3 months) → 90% (6 months)
- **Unit Tests:** 46.08% → 85% → 95%
- **Integration Tests:** 0% → 60% → 80%
- **Performance Tests:** 0% → 50% → 70%

### Test Counts
- **Unit Tests:** 12 → 150+
- **Integration Tests:** 0 → 30+
- **Performance Tests:** 0 → 20+

### Quality Gates
- ✅ All tests passing
- ✅ Coverage ≥80%
- ✅ Performance within 20% of baseline
- ✅ No critical security issues
- ✅ Type checking passes
- ✅ Linting passes

---

## Resource Requirements

### Timeline
- **Week 1:** Test infrastructure (40 hours)
- **Weeks 2-3:** Unit tests (60 hours)
- **Week 4:** Performance tests (30 hours)
- **Weeks 5-6:** Integration tests (40 hours)
- **Weeks 7-8:** Load testing (30 hours)
- **Total:** ~200 hours

### Team
- 1 Senior Test Engineer (lead)
- 1 Developer (test implementation)
- Code reviews by SDK maintainers

---

## Risk Mitigation

### High-Risk Areas
1. **WebSocket streaming** - Zero coverage, production-critical
2. **Error recovery** - Untested retry logic
3. **Connection pooling** - No stress testing
4. **Large files** - No validation >10MB

### Mitigation Strategy
- Prioritise high-risk areas first
- Add tests before refactoring
- Use mocks to enable testing without API
- Continuous monitoring in CI/CD

---

## Next Steps (This Week)

1. ✅ **Today:** Fix 2 failing tests
2. ✅ **Day 2:** Create `conftest.py` with fixtures
3. ✅ **Day 3:** Add HTTP response mocking
4. ✅ **Day 4:** Implement 20 HTTP client unit tests
5. ✅ **Day 5:** Implement 15 WebSocket unit tests

**Review Point:** Friday - Coverage should be >60%

---

## Conclusion

The Soniox Pro SDK requires immediate investment in testing to achieve production readiness. The roadmap above provides a clear path from 46% to 90% coverage over 8 weeks.

**Critical Priority Items:**
1. Fix failing tests (2 hours)
2. Set up test infrastructure (8 hours)
3. HTTP client tests (20 hours)
4. WebSocket tests (20 hours)
5. Performance benchmarks (30 hours)

**Total Immediate Effort:** 80 hours over 2 weeks

This investment will significantly reduce production risks and establish a foundation for continuous quality assurance.
