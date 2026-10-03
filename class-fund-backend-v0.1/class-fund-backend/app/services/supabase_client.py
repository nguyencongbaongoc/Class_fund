"""Supabase integration adapters."""
import os
from typing import Optional

from supabase import create_client, Client
from postgrest import APIError


class SupabaseConfig:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
    def validate(self) -> bool:
        return all([self.url, self.service_key, self.anon_key])


class SupabaseClient:
    """Wrapper for Supabase client with proper error handling."""
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or SupabaseConfig()
        self._admin_client: Optional[Client] = None
        self._anon_client: Optional[Client] = None
        
    @property
    def admin(self) -> Client:
        """Get admin client (service role) - server-side only."""
        if self._admin_client is None:
            if not self.config.service_key:
                raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not configured")
            self._admin_client = create_client(self.config.url, self.config.service_key)
        return self._admin_client
    
    @property
    def anon(self) -> Client:
        """Get anonymous client - for frontend/public operations."""
        if self._anon_client is None:
            if not self.config.anon_key:
                raise RuntimeError("SUPABASE_ANON_KEY not configured")
            self._anon_client = create_client(self.config.url, self.config.anon_key)
        return self._anon_client
    
    def get_user_client(self, access_token: str) -> Client:
        """Get client authenticated as specific user."""
        client = create_client(self.config.url, self.config.anon_key)
        client.auth.set_session(access_token, "")
        return client
    
    # Storage operations
    def upload_receipt(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        """Upload receipt to Supabase Storage. Returns public URL."""
        bucket = "receipts"
        path = f"uploads/{file_name}"
        try:
            self.admin.storage.from_(bucket).upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            return self.admin.storage.from_(bucket).get_public_url(path)
        except APIError as e:
            if "already exists" in str(e):
                # Return existing URL
                return self.admin.storage.from_(bucket).get_public_url(path)
            raise
    
    def download_receipt(self, path: str) -> bytes:
        """Download receipt from Supabase Storage."""
        bucket = "receipts"
        return self.admin.storage.from_(bucket).download(path)
    
    def delete_receipt(self, path: str) -> bool:
        """Delete receipt from Supabase Storage."""
        bucket = "receipts"
        try:
            self.admin.storage.from_(bucket).remove([path])
            return True
        except APIError:
            return False
    
    # Realtime subscriptions
    def subscribe_to_messages(self, conversation_id: str, callback):
        """Subscribe to message changes in a conversation."""
        channel = self.admin.channel(f"messages:{conversation_id}")
        channel.on(
            "postgres_changes",
            {
                "event": "*",
                "schema": "public",
                "table": "messages",
                "filter": f"conversation_id=eq.{conversation_id}"
            },
            callback
        )
        channel.subscribe()
        return channel
    
    def subscribe_to_worker_status(self, callback):
        """Subscribe to worker status changes."""
        channel = self.admin.channel("worker_status")
        channel.on(
            "postgres_changes",
            {
                "event": "*",
                "schema": "public",
                "table": "worker_status"
            },
            callback
        )
        channel.subscribe()
        return channel
    
    # Auth operations
    def verify_jwt(self, token: str) -> dict:
        """Verify JWT and return claims."""
        try:
            # Supabase JWT verification
            response = self.admin.auth.get_user(token)
            return response.user.model_dump() if response.user else {}
        except Exception:
            return {}
    
    def get_user_by_id(self, user_id: str) -> dict:
        """Get user by ID (admin only)."""
        try:
            response = self.admin.auth.admin.get_user_by_id(user_id)
            return response.user.model_dump() if response.user else {}
        except Exception:
            return {}
    
    # RLS policy helpers
    def enable_rls(self, table: str):
        """Enable RLS on a table (admin only)."""
        self.admin.rpc("enable_rls", {"table_name": table}).execute()
    
    def create_policy(self, table: str, policy_name: str, definition: str, roles: list = None):
        """Create RLS policy (admin only)."""
        self.admin.rpc("create_policy", {
            "table_name": table,
            "policy_name": policy_name,
            "definition": definition,
            "roles": roles or ["anon", "authenticated"]
        }).execute()


# Global instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client


def init_supabase(config: SupabaseConfig):
    """Initialize Supabase with custom config."""
    global _supabase_client
    _supabase_client = SupabaseClient(config)


# Health check
def check_supabase_connection() -> bool:
    """Check if Supabase is reachable."""
    try:
        client = get_supabase_client()
        # Simple query to test connection
        client.admin.table("messages").select("id").limit(1).execute()
        return True
    except Exception:
        return False