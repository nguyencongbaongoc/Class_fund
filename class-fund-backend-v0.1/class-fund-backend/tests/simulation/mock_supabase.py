"""Mock Supabase Client for simulation testing."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from app.services.supabase_client import SupabaseClient, SupabaseConfig

from tests.simulation.config import get_simulation_config, MockChannel

logger = logging.getLogger(__name__)


class MockSupabaseClient:
    """Test-only mock Supabase client with deterministic behavior."""
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or SupabaseConfig()
        self.sim_config = get_simulation_config()
        self._admin_client = None
        self._anon_client = None
    
    # Auth operations
    def verify_jwt(self, token: str) -> Dict:
        """Verify JWT and return claims based on mock users."""
        # In simulation, token format: "mock-token-{user_id}"
        if token.startswith("mock-token-"):
            user_id = token.replace("mock-token-", "")
            user = self.sim_config.supabase_users.get(user_id)
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role.value,
                    "name": user.name
                }
        # Invalid token
        return {}
    
    def get_user_by_id(self, user_id: str) -> Dict:
        """Get user by ID."""
        user = self.sim_config.supabase_users.get(user_id)
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "role": user.role.value,
                "name": user.name
            }
        return {}
    
    # Storage operations
    def upload_receipt(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        """Upload receipt to mock storage. Returns fake public URL."""
        if self.sim_config.inject_storage_failure:
            raise Exception("Storage upload failed (injected)")
        
        path = f"uploads/{file_name}"
        self.sim_config.add_storage_file(path, file_bytes)
        
        # Return fake public URL
        return f"https://mock-storage.supabase.co/storage/v1/object/public/receipts/{path}"
    
    def download_receipt(self, path: str) -> bytes:
        """Download receipt from mock storage."""
        if self.sim_config.inject_storage_failure:
            raise Exception("Storage download failed (injected)")
        
        content = self.sim_config.get_storage_file(path)
        if content is None:
            raise Exception(f"File not found: {path}")
        return content
    
    def delete_receipt(self, path: str) -> bool:
        """Delete receipt from mock storage."""
        if self.sim_config.inject_storage_failure:
            raise Exception("Storage delete failed (injected)")
        
        if path in self.sim_config.supabase_storage:
            del self.sim_config.supabase_storage[path]
            return True
        return False
    
    # Realtime subscriptions
    def subscribe_to_messages(self, conversation_id: str, callback: Callable) -> MockChannel:
        """Subscribe to message changes in a conversation."""
        if self.sim_config.inject_realtime_disconnect:
            channel = MockChannel(f"messages:{conversation_id}")
            channel.subscribed = False
            return channel
        
        channel = self.sim_config.create_realtime_channel(f"messages:{conversation_id}")
        # Wrap callback to handle mock payload format
        original_callback = callback
        def wrapped_callback(payload):
            original_callback(payload)
        channel.on("postgres_changes", {"event": "*", "schema": "public", "table": "messages"}, wrapped_callback)
        channel.subscribe()
        return channel
    
    def subscribe_to_worker_status(self, callback: Callable) -> MockChannel:
        """Subscribe to worker status changes."""
        if self.sim_config.inject_realtime_disconnect:
            channel = MockChannel("worker_status")
            channel.subscribed = False
            return channel
        
        channel = self.sim_config.create_realtime_channel("worker_status")
        original_callback = callback
        def wrapped_callback(payload):
            original_callback(payload)
        channel.on("postgres_changes", {"event": "*", "schema": "public", "table": "worker_status"}, wrapped_callback)
        channel.subscribe()
        return channel
    
    # RLS policy helpers (mock - no-op)
    def enable_rls(self, table: str):
        """Enable RLS on a table (mock)."""
        logger.info(f"Mock: enable_rls({table})")
    
    def create_policy(self, table: str, policy_name: str, definition: str, roles: List = None):
        """Create RLS policy (mock)."""
        logger.info(f"Mock: create_policy({table}, {policy_name})")
    
    # Health check
    def check_connection(self) -> bool:
        """Check if Supabase is reachable."""
        return self.sim_config.supabase_available
    
    def close(self):
        """Close the client."""
        pass


# Property accessors to match real client interface
@property
def admin(self):
    """Get admin client (mock)."""
    return self

@property
def anon(self):
    """Get anonymous client (mock)."""
    return self

MockSupabaseClient.admin = admin
MockSupabaseClient.anon = anon


# Helper functions for test setup
def create_mock_user_token(user_id: str) -> str:
    """Create a mock JWT token for a user."""
    return f"mock-token-{user_id}"


def create_mock_admin_token() -> str:
    return create_mock_user_token("owner-1")


def create_mock_moderator_token() -> str:
    return create_mock_user_token("moderator-1")


def create_mock_member_token() -> str:
    return create_mock_user_token("member-1")


def create_mock_public_token() -> str:
    return create_mock_user_token("public-1")


def create_mock_invalid_token() -> str:
    return "mock-token-invalid"


def create_mock_expired_token() -> str:
    return "mock-token-expired"


def create_mock_malformed_token() -> str:
    return "malformed-token"