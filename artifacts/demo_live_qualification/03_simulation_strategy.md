# Simulation Strategy

## Overview
Design a test-only integration environment that uses deterministic mocks at external service boundaries while executing real application code for business logic.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SIMULATION ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌─────────────────────┐     ┌────────────────────┐   │
│  │   FRONTEND   │────▶│    BACKEND API      │────▶│   TEST DATABASE    │   │
│  │  (React)     │     │   (FastAPI)         │     │   (SQLite/Postgres)│   │
│  └──────────────┘     └──────────┬──────────┘     └────────────────────┘   │
│                                 │                                          │
│                    ┌────────────┼────────────┐                             │
│                    ▼            ▼            ▼                             │
│           ┌──────────────┐ ┌──────────┐ ┌───────────┐                     │
│           │  MOCK OLLAMA │ │MOCK SUPAB│ │ MOCK WORKER│                     │
│           │ (Deterministic)│ │  (Auth/  │ │ (Controlled)│                     │
│           │  Fixtures)    │ │ Storage/ │ │  Lifecycle)│                     │
│           └──────────────┘ └──────────┘ └───────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Design Principles

1. **Real Application Code** - Execute actual FastAPI routes, services, models
2. **Mock Only at Boundaries** - External services (Ollama, Supabase, Worker queue)
3. **Deterministic Fixtures** - Fixed responses for reproducible tests
4. **Isolated State** - Each test gets clean database, reset mocks
5. **No Production Leaks** - Test config never touches real credentials
6. **Explicit Test-Only Implementations** - Clear `TestXxx` naming

## Mock Strategy by Component

### 1. Database (PostgreSQL → SQLite)
**Approach**: Use existing in-memory SQLite pattern from tests
**Implementation**: `app/db/session.py` already supports test override via `get_db` dependency
**Files**: No changes needed - existing test infrastructure works

### 2. Ollama Vision/Text Client
**Interface**: `app/services/ollama_client.py` - `OllamaVisionClient`
**Mock Class**: `MockOllamaVisionClient` (test-only)
**Methods to Mock**:
- `extract_from_image()` → deterministic `VisionResult`
- `extract_with_text_fallback()` → deterministic `VisionResult`
- `is_available()` → `True`
- `list_models()` → `["qwen2.5vl:3b", "qwen3.5:4b"]`
- `get_circuit_state()` → `CircuitState.CLOSED`

**Fixtures**:
```python
# Success cases
VISION_SUCCESS_RECEIPT = VisionResult(
    transaction_code="FT26277123456789",
    amount=500000,
    sender_name="NGUYEN VAN A",
    bank_name="Vietcombank",
    transaction_time="2026-10-04T10:30:00Z",
    confidence=0.95,
    raw_text="...",
    needs_human_review=False
)

VISION_LOW_CONFIDENCE = VisionResult(..., confidence=0.5, needs_human_review=True)
VISION_MISSING_FIELDS = VisionResult(transaction_code=None, amount=None, ...)

# Failure cases
VISION_TIMEOUT = VisionResult(error="Request timeout", needs_human_review=True)
VISION_CONNECTION_REFUSED = VisionResult(error="Connection refused", needs_human_review=True)
VISION_INVALID_JSON = VisionResult(error="Failed to parse model output", needs_human_review=True)
VISION_MODEL_UNAVAILABLE = VisionResult(error="Model not available", needs_human_review=True)
```

**Injection**: Override `get_vision_client()` dependency in FastAPI

### 3. Supabase Client
**Interface**: `app/services/supabase_client.py` - `SupabaseClient`
**Mock Class**: `MockSupabaseClient` (test-only)

**Auth Mock**:
- `verify_jwt(token)` → returns user claims based on test token
- `get_user_by_id(user_id)` → returns test user

**Storage Mock**:
- `upload_receipt()` → returns fake public URL, stores in memory
- `download_receipt()` → returns stored bytes
- `delete_receipt()` → removes from memory

**Realtime Mock**:
- `subscribe_to_messages()` → returns mock channel with `emit()` method
- `subscribe_to_worker_status()` → returns mock channel

**Injection**: Override `get_supabase_client()` dependency

### 4. Worker Simulation
**Interface**: `worker/main.py` - `Worker` class
**Simulator**: `WorkerSimulator` (test-only) - controls lifecycle explicitly

**Methods**:
- `start()` → sets status ONLINE
- `claim_next()` → returns next pending message or None
- `process_message(message)` → processes synchronously
- `heartbeat()` → updates last_heartbeat
- `crash()` → sets status OFFLINE, leaves lease
- `recover()` → reclaims stale leases, restarts
- `stop()` → sets status STOPPED

**State Machine**:
```
STARTING → ONLINE → (process) → ONLINE
                ↓ crash
             OFFLINE → RECOVERING → ONLINE
                ↓ stop
             STOPPED
```

**Failure Injection Points**:
- Crash during processing
- Crash after external call but before ack
- Lease expiry
- Duplicate delivery
- Heartbeat timeout

### 5. Configuration Management
**Central Config**: `tests/simulation_config.py`

```python
class SimulationConfig:
    # Database
    database_url = "sqlite+pysqlite:///:memory:"
    
    # Ollama
    ollama_vision_responses: Dict[str, VisionResult] = {}
    ollama_text_responses: Dict[str, VisionResult] = {}
    ollama_available: bool = True
    ollama_models: List[str] = ["qwen2.5vl:3b", "qwen3.5:4b"]
    circuit_state: CircuitState = CircuitState.CLOSED
    
    # Supabase
    supabase_users: Dict[str, User] = {}
    supabase_storage: Dict[str, bytes] = {}
    supabase_realtime_channels: List[MockChannel] = []
    
    # Worker
    worker_state: WorkerState = WorkerState.OFFLINE
    worker_lease_duration: int = 300
    worker_crash_on_process: bool = False
    worker_crash_after_external: bool = False
    
    # Failure injection
    inject_db_timeout: bool = False
    inject_storage_failure: bool = False
    inject_realtime_disconnect: bool = False
    
    def reset(self):
        """Reset all simulation state between tests."""
        ...
```

## Test Layers

### Layer 1: Unit Tests for Simulation Adapters
- Test `MockOllamaVisionClient` returns correct fixtures
- Test `MockSupabaseClient` auth/storage/realtime behavior
- Test `WorkerSimulator` state transitions

### Layer 2: Service Contract Tests
- Test `ledger.py` functions with test DB
- Test `verify_and_post_from_ai()` with mock Ollama
- Test review API endpoints with mock auth

### Layer 3: API Integration Tests
- Full FastAPI app with mocked dependencies
- Test all routes: auth, uploads, vision, review, admin
- Verify request/response schemas

### Layer 4: Worker/Queue Lifecycle Tests
- Worker startup, claim, process, complete
- Lease expiry and recovery
- Retry backoff
- Crash recovery
- Concurrent workers

### Layer 5: End-to-End Financial Workflow Simulations
- Scenario A: Normal financial workflow
- Scenario B: Human rejects proposal
- Scenario C: Duplicate receipt
- Scenario D: Recall before posting
- Scenario E: Recall after posting (reversal)
- Scenario F: External service failures
- Scenario G: Admin dashboard views

### Layer 6: Frontend/Backend Contract Tests
- API schema compatibility
- Auth header propagation
- Role mapping
- Error handling
- Pagination/filtering
- CSV exports

### Layer 7: Security & Financial Invariant Regression
- All invariants from `ledger.py` re-validated
- Authorization bypass attempts
- Token replay protection
- Double reversal prevention

## Test Execution Strategy

### Runner Options
**Option A: Pytest with Custom Fixtures** (Preferred - matches existing)
```python
# conftest.py
@pytest.fixture
def simulation_config():
    config = SimulationConfig()
    yield config
    config.reset()

@pytest.fixture
def test_app(simulation_config):
    app = create_app(override_dependencies=simulation_config.get_overrides())
    return TestClient(app)
```

**Option B: Dedicated Runner Script** (If pytest insufficient)
```
python -m scripts.simulation_runner preflight
python -m scripts.simulation_runner run --layer=all
python -m scripts.simulation_runner report
```

### Test Data Management
- **Fixtures**: `tests/fixtures/` - JSON/YAML test data
- **Factories**: `tests/factories.py` - Create test entities
- **Snapshots**: `tests/snapshots/` - Expected responses

## Isolation Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| No real DB | SQLite in-memory / test PostgreSQL |
| No real Ollama | Mock client with fixed responses |
| No real Supabase | Mock client with in-memory state |
| No real network | All HTTP calls mocked |
| No credential leaks | Test config uses only fake values |
| Test isolation | Config.reset() between each test |
| No production code paths | Explicit test-only imports |

## Reporting

### Machine-Readable: `simulation_results.json`
```json
{
  "timestamp": "2026-10-04T...",
  "phase": "DEMO_LIVE_QUALIFICATION",
  "scenarios": [
    {
      "id": "scenario_a_normal_workflow",
      "status": "PASS",
      "duration_ms": 1234,
      "details": {...}
    }
  ],
  "invariants": [
    {"name": "no_unauthorized_posting", "status": "PASS"}
  ],
  "summary": {
    "total": 50,
    "passed": 48,
    "failed": 0,
    "blocked": 2,
    "skipped": 0
  }
}
```

### Human-Readable: Markdown artifacts per component

## Known Limitations
1. **No real PostgreSQL RLS testing** - Application-level auth only
2. **No real Supabase Realtime** - Event emitter simulation only
3. **No real Ollama inference** - Deterministic fixtures only
4. **No browser automation** - API-level only unless existing E2E exists
5. **Worker timing** - Synchronous simulation, not real async

## Implementation Order
1. Create simulation config and mock classes
2. Add pytest fixtures for dependency injection
3. Implement Layer 1-2 tests
4. Implement Layer 3 API tests
5. Implement Layer 4 worker tests
6. Implement Layer 5 E2E scenarios
7. Implement Layer 6 frontend contract tests
8. Implement Layer 7 invariant tests
9. Generate reports
10. Final qualification