"""Legacy Supabase client - DEPRECATED.
This module is kept for backward compatibility with tests.
All Supabase functionality has been replaced with local implementations:
- Storage: Local filesystem (app/api/routes/uploads.py)
- Realtime: WebSocket + Redis Pub/Sub (app/services/realtime.py)
- Auth: Local JWT (app/core/security.py)
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class SupabaseConfig:
    """Deprecated Supabase configuration."""
    url: Optional[str] = None
    service_key: Optional[str] = None
    anon_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    
    def validate(self) -> bool:
        return False  # Always false - Supabase not configured


class SupabaseClient:
    """Deprecated Supabase client - all methods raise NotImplementedError."""
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or SupabaseConfig()
    
    # All methods deprecated - raise NotImplementedError
    def upload_receipt(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        raise NotImplementedError("Supabase Storage replaced with local filesystem")
    
    def download_receipt(self, path: str) -> bytes:
        raise NotImplementedError("Supabase Storage replaced with local filesystem")
    
    def delete_receipt(self, path: str) -> bool:
        raise NotImplementedError("Supabase Storage replaced with local filesystem")
    
    def subscribe_to_messages(self, conversation_id: str, callback):
        raise NotImplementedError("Supabase Realtime replaced with WebSocket + Redis")
    
    def subscribe_to_worker_status(self, callback):
        raise NotImplementedError("Supabase Realtime replaced with WebSocket + Redis")
    
    def verify_jwt(self, token: str) -> dict:
        raise NotImplementedError("Supabase Auth replaced with local JWT")
    
    def get_user_by_id(self, user_id: str) -> dict:
        raise NotImplementedError("Supabase Auth replaced with local DB query")
    
    def enable_rls(self, table: str):
        raise NotImplementedError("Supabase RLS replaced with app-level authorization")
    
    def create_policy(self, table: str, policy_name: str, definition: str, roles: list = None):
        raise NotImplementedError("Supabase RLS replaced with app-level authorization")


# Global instance (for backward compatibility with tests)
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get Supabase client (deprecated - raises NotImplementedError on use)."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client


def init_supabase(config: SupabaseConfig):
    """Initialize Supabase with custom config (deprecated)."""
    global _supabase_client
    _supabase_client = SupabaseClient(config)


# Health check
def check_supabase_connection() -> bool:
    """Check if Supabase is reachable (always returns False - not configured)."""
    return False