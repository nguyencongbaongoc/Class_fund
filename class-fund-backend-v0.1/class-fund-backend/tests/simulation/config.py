"""Central simulation configuration and state management."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.services.ollama_client import CircuitState, VisionResult
from app.models.models import User, Role


class WorkerState(str, Enum):
    STARTING = "STARTING"
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    RECOVERING = "RECOVERING"
    STOPPED = "STOPPED"


class MockChannel:
    """Mock Supabase Realtime channel."""
    
    def __init__(self, name: str):
        self.name = name
        self.subscribed = False
        self.callbacks: List[callable] = []
        self.events: List[Dict[str, Any]] = []
    
    def on(self, event_type: str, filter_dict: Dict, callback: callable):
        self.callbacks.append({"event": event_type, "filter": filter_dict, "callback": callback})
    
    def subscribe(self):
        self.subscribed = True
    
    def unsubscribe(self):
        self.subscribed = False
    
    def emit(self, payload: Dict[str, Any]):
        """Emit event to all matching callbacks."""
        self.events.append(payload)
        for cb in self.callbacks:
            try:
                cb(payload)
            except Exception:
                pass


@dataclass
class SimulationConfig:
    """Central configuration for all simulation components."""
    
    # Database
    database_url: str = "sqlite+pysqlite:///:memory:"
    
    # Ollama Vision/Text
    ollama_vision_responses: Dict[str, VisionResult] = field(default_factory=dict)
    ollama_text_responses: Dict[str, VisionResult] = field(default_factory=dict)
    ollama_available: bool = True
    ollama_models: List[str] = field(default_factory=lambda: ["qwen2.5vl:3b", "qwen3.5:4b"])
    circuit_state: CircuitState = CircuitState.CLOSED
    vision_call_count: int = 0
    text_fallback_call_count: int = 0
    
    # Supabase
    supabase_users: Dict[str, User] = field(default_factory=dict)
    supabase_storage: Dict[str, bytes] = field(default_factory=dict)
    supabase_realtime_channels: List[MockChannel] = field(default_factory=list)
    supabase_available: bool = True
    
    # Worker
    worker_state: WorkerState = WorkerState.OFFLINE
    worker_lease_duration: int = 300
    worker_id: str = "test-worker"
    worker_crash_on_process: bool = False
    worker_crash_after_external: bool = False
    worker_heartbeat_interval: int = 10
    claimed_messages: Dict[str, datetime] = field(default_factory=dict)
    message_leases: Dict[str, datetime] = field(default_factory=dict)
    
    # Failure Injection
    inject_db_timeout: bool = False
    inject_storage_failure: bool = False
    inject_realtime_disconnect: bool = False
    inject_ollama_timeout: bool = False
    inject_ollama_connection_refused: bool = False
    inject_worker_crash: bool = False
    inject_lease_expiry: bool = False
    
    # Test tracking
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    current_test: Optional[str] = None
    _lock: threading.RLock = field(default_factory=threading.RLock)
    
    def __post_init__(self):
        """Initialize default test users."""
        if not self.supabase_users:
            self.supabase_users = {
                "owner-1": User(
                    id="owner-1",
                    name="Test Owner",
                    email="owner@test.com",
                    password_hash="hashed",
                    role=Role.OWNER_TREASURER,
                    created_at=datetime.now(timezone.utc)
                ),
                "moderator-1": User(
                    id="moderator-1",
                    name="Test Moderator",
                    email="moderator@test.com",
                    password_hash="hashed",
                    role=Role.MODERATOR,
                    created_at=datetime.now(timezone.utc)
                ),
                "member-1": User(
                    id="member-1",
                    name="Test Member",
                    email="member@test.com",
                    password_hash="hashed",
                    role=Role.MEMBER,
                    created_at=datetime.now(timezone.utc)
                ),
                "public-1": User(
                    id="public-1",
                    name="Test Public",
                    email="public@test.com",
                    password_hash="hashed",
                    role=Role.PUBLIC,
                    created_at=datetime.now(timezone.utc)
                ),
            }
    
    def set_vision_response(self, key: str, result: VisionResult):
        """Set a deterministic vision response for a test case."""
        with self._lock:
            self.ollama_vision_responses[key] = result
    
    def set_text_response(self, key: str, result: VisionResult):
        """Set a deterministic text fallback response."""
        with self._lock:
            self.ollama_text_responses[key] = result
    
    def get_vision_response(self, key: str) -> Optional[VisionResult]:
        """Get vision response for a test case."""
        with self._lock:
            self.vision_call_count += 1
            return self.ollama_vision_responses.get(key)
    
    def get_text_response(self, key: str) -> Optional[VisionResult]:
        """Get text fallback response."""
        with self._lock:
            self.text_fallback_call_count += 1
            return self.ollama_text_responses.get(key)
    
    def add_storage_file(self, path: str, content: bytes):
        """Add file to mock storage."""
        with self._lock:
            self.supabase_storage[path] = content
    
    def get_storage_file(self, path: str) -> Optional[bytes]:
        """Get file from mock storage."""
        with self._lock:
            return self.supabase_storage.get(path)
    
    def create_realtime_channel(self, name: str) -> MockChannel:
        """Create a mock realtime channel."""
        with self._lock:
            channel = MockChannel(name)
            self.supabase_realtime_channels.append(channel)
            return channel
    
    def reset(self):
        """Reset all simulation state for test isolation."""
        with self._lock:
            self.ollama_vision_responses.clear()
            self.ollama_text_responses.clear()
            self.ollama_available = True
            self.circuit_state = CircuitState.CLOSED
            self.vision_call_count = 0
            self.text_fallback_call_count = 0
            
            self.supabase_storage.clear()
            self.supabase_realtime_channels.clear()
            self.supabase_available = True
            
            self.worker_state = WorkerState.OFFLINE
            self.worker_crash_on_process = False
            self.worker_crash_after_external = False
            self.claimed_messages.clear()
            self.message_leases.clear()
            
            self.inject_db_timeout = False
            self.inject_storage_failure = False
            self.inject_realtime_disconnect = False
            self.inject_ollama_timeout = False
            self.inject_ollama_connection_refused = False
            self.inject_worker_crash = False
            self.inject_lease_expiry = False
            
            self.current_test = None
    
    def start_test(self, test_name: str):
        """Mark test start for tracking."""
        with self._lock:
            self.current_test = test_name
            self.reset()
    
    def record_result(self, test_name: str, status: str, duration_ms: int, details: Dict = None):
        """Record test result."""
        with self._lock:
            self.test_results.append({
                "test": test_name,
                "status": status,
                "duration_ms": duration_ms,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })


# Global simulation config instance
_simulation_config: Optional[SimulationConfig] = None
_config_lock = threading.RLock()


def get_simulation_config() -> SimulationConfig:
    """Get global simulation config (singleton)."""
    global _simulation_config
    with _config_lock:
        if _simulation_config is None:
            _simulation_config = SimulationConfig()
        return _simulation_config


def reset_simulation_config():
    """Reset global simulation config."""
    global _simulation_config
    with _config_lock:
        if _simulation_config:
            _simulation_config.reset()
        _simulation_config = None


def set_simulation_config(config: SimulationConfig):
    """Set global simulation config (for testing)."""
    global _simulation_config
    with _config_lock:
        _simulation_config = config