# 01 Environment and Isolation Preflight

## Repository Baseline

- **Repository Path**: `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB`
- **Current Branch**: `master`
- **HEAD Commit**: `f7ac634` - "Merge Phase 3 AI Pipeline + Phase 4 Guest Chat"
- **Git Status**: Working tree has modifications (see `02_repository_baseline.md` for details)
- **Python Interpreter**: Python 3.12.10
- **Virtual Environment**: Using system Python with installed packages
- **Test Dependencies**: pytest 9.1.1, pytest-asyncio, httpx
- **Node.js/npm**: Available (frontend build possible)

## Isolation Verification

### 1. Database Isolation ✅
- **Configuration**: `os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"` set in `tests/conftest.py:8`
- **Verification**: All tests use in-memory SQLite database created fresh per test session
- **Production DB**: No production database URL present in test configuration

### 2. External Service Mocking ✅
- **Ollama**: Mocked via `MockOllamaVisionClient` in `tests/simulation/mock_ollama.py`
- **Supabase**: Mocked via `MockSupabaseClient` in `tests/simulation/mock_supabase.py`
- **Network**: No external network calls in test suite

### 3. Worker Execution Isolation ✅
- **Queue**: Simulated via `WorkerSimulator` in `tests/simulation/mock_worker.py`
- **Real Queue**: No real message queue (Redis, RabbitMQ, etc.) used in tests
- **Worker Processes**: No actual worker processes spawned; all simulation in test process

### 4. AI Calls Mocked ✅
- **Ollama Vision**: Deterministic mock responses via `create_vision_success_receipt()`, `create_vision_low_confidence()`, etc.
- **Failure Injection**: Controlled via `sim_config.inject_ollama_timeout`, `inject_ollama_connection_refused`, etc.

### 5. No External Dependencies ✅
- No real banking/payment services
- No external storage (Supabase Storage mocked)
- No real notification services
- No external API calls

### 6. Test Data Isolation ✅
- All test data created in-memory per test function
- `db_session` fixture uses transaction rollback per test
- `sim_config.reset()` called between tests
- No persistent test data

## Environment Evidence

### Test Configuration (conftest.py)
```python
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AI_CONFIDENCE_THRESHOLD"] = "0.9"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
os.environ["OLLAMA_VISION_MODEL"] = "qwen2.5vl:3b"
os.environ["OLLAMA_TEXT_MODEL"] = "qwen3.5:4b"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-service-key"
os.environ["SUPABASE_ANON_KEY"] = "mock-anon-key"
os.environ["SUPABASE_JWT_SECRET"] = "mock-jwt-secret"
```

### Mock Service Injection (conftest.py:102-125)
```python
@pytest.fixture(scope="function")
def mock_ollama(sim_config):
    sim_config.reset()
    client = MockOllamaVisionClient()
    import app.services.ollama_client as ollama_module
    original_get = ollama_module.get_vision_client
    ollama_module.get_vision_client = lambda: client
    yield client
    ollama_module.get_vision_client = original_get
    sim_config.reset()
```

### Worker Simulation (mock_worker.py)
- `WorkerSimulator` class simulates worker lifecycle without real processes
- `create_test_worker()` creates simulator with fresh state
- All operations are synchronous in-test calls

## Isolation Verdict: ✅ ISOLATED

All isolation requirements verified. Test environment cannot:
- Connect to production database
- Access real Supabase services
- Contact real Ollama endpoints
- Execute real financial transactions
- Spawn real worker processes
- Modify production data

Proceeding with qualification testing.