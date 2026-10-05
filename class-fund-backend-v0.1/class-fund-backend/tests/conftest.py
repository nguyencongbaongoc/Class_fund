"""Pytest configuration and fixtures for simulation testing."""
from __future__ import annotations

import os
import sys

# Set test database URL BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AI_CONFIDENCE_THRESHOLD"] = "0.9"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
os.environ["OLLAMA_VISION_MODEL"] = "qwen2.5vl:3b"
os.environ["OLLAMA_TEXT_MODEL"] = "qwen3.5:4b"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-service-key"
os.environ["SUPABASE_ANON_KEY"] = "mock-anon-key"
os.environ["SUPABASE_JWT_SECRET"] = "mock-jwt-secret"

from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)
sys.path.insert(0, os.path.join(backend_root, "tests"))

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    LedgerStatus, Message, MessageStatus, Transaction, Upload, UploadStatus, User, Role
)
from app.core.security import hash_password
from app.services.ledger import calculate_balance, post_transaction, verify_and_post_from_ai
from app.services.ollama_client import VisionResult

from tests.simulation.config import get_simulation_config, reset_simulation_config
from tests.simulation.mock_ollama import MockOllamaVisionClient
from tests.simulation.mock_supabase import MockSupabaseClient


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine (in-memory SQLite)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, future=True)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db(db_session: Session) -> Generator[Session, None, None]:
    """Alias for db_session."""
    yield db_session


# ============================================================================
# Simulation Config Fixture
# ============================================================================

@pytest.fixture(scope="function")
def sim_config():
    """Provide simulation config with automatic reset between tests."""
    config = get_simulation_config()
    config.reset()
    yield config
    config.reset()


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_ollama(sim_config):
    """Provide mock Ollama client with fresh state for each test."""
    sim_config.reset()
    client = MockOllamaVisionClient()
    # Override the global get_vision_client
    import app.services.ollama_client as ollama_module
    original_get = ollama_module.get_vision_client
    ollama_module.get_vision_client = lambda: client
    yield client
    ollama_module.get_vision_client = original_get
    sim_config.reset()


@pytest.fixture(scope="function")
def mock_supabase(sim_config):
    """Provide mock Supabase client."""
    client = MockSupabaseClient()
    # Override the global get_supabase_client
    import app.services.supabase_client as supabase_module
    original_get = supabase_module.get_supabase_client
    supabase_module.get_supabase_client = lambda: client
    yield client
    supabase_module.get_supabase_client = original_get


# ============================================================================
# FastAPI Test Client Fixture
# ============================================================================

@pytest.fixture(scope="function")
def test_client(db_session: Session, mock_ollama, mock_supabase) -> Generator[TestClient, None, None]:
    """Create test client with overridden dependencies."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def test_account(db: Session) -> Account:
    """Create a test fund account."""
    account = Account(
        name="Test Fund",
        currency="VND",
        opening_balance=Decimal("1000000"),
        active=True
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_bank_account(db: Session) -> BankAccount:
    """Create a test bank account."""
    bank = BankAccount(
        bank_name="Vietcombank",
        account_name="Test Fund",
        account_number="1234567890",
        active=True
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


@pytest.fixture
def test_user_owner(db: Session) -> User:
    """Create a test OWNER_TREASURER user."""
    user = User(
        id="owner-1",
        name="Test Owner",
        email="owner@test.com",
        password_hash=hash_password("password"),
        role=Role.OWNER_TREASURER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_moderator(db: Session) -> User:
    """Create a test MODERATOR user."""
    user = User(
        id="moderator-1",
        name="Test Moderator",
        email="moderator@test.com",
        password_hash=hash_password("password"),
        role=Role.MODERATOR
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_member(db: Session) -> User:
    """Create a test MEMBER user."""
    user = User(
        id="member-1",
        name="Test Member",
        email="member@test.com",
        password_hash=hash_password("password"),
        role=Role.MEMBER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_public(db: Session) -> User:
    """Create a test PUBLIC user."""
    user = User(
        id="public-1",
        name="Test Public",
        email="public@test.com",
        password_hash=hash_password("password"),
        role=Role.PUBLIC
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_upload(db: Session, test_user_member: User) -> Upload:
    """Create a test upload."""
    upload = Upload(
        file_hash="a" * 64,
        original_filename="receipt.png",
        storage_path="uploads/receipt.png",
        uploaded_by=test_user_member.id,
        uploader_name=test_user_member.name,
        status=UploadStatus.PENDING
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


@pytest.fixture
def test_extraction(db: Session, test_upload: Upload, test_bank_account: BankAccount) -> ExtractedTransaction:
    """Create a test extraction with high confidence."""
    extraction = ExtractedTransaction(
        upload_id=test_upload.id,
        transaction_code="FT26277123456789",
        amount=Decimal("500000"),
        sender_name="NGUYEN VAN A",
        bank_name="Vietcombank",
        bank_account_id=test_bank_account.id,
        transaction_time=datetime.now(timezone.utc),
        confidence=Decimal("0.95"),
        status=UploadStatus.PROCESSING,
        currency="VND"
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction


@pytest.fixture
def test_extraction_low_confidence(db: Session, test_upload: Upload, test_bank_account: BankAccount) -> ExtractedTransaction:
    """Create a test extraction with low confidence (needs review)."""
    extraction = ExtractedTransaction(
        upload_id=test_upload.id,
        transaction_code="FT26277123456789",
        amount=Decimal("500000"),
        sender_name="NGUYEN VAN A",
        bank_name="Vietcombank",
        bank_account_id=test_bank_account.id,
        transaction_time=datetime.now(timezone.utc),
        confidence=Decimal("0.5"),
        status=UploadStatus.PROCESSING,
        currency="VND"
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction


@pytest.fixture
def test_message(db: Session, test_upload: Upload, test_user_member: User) -> Message:
    """Create a test message."""
    message = Message(
        conversation_id="conv-1",
        sender_id=test_user_member.id,
        sender_name=test_user_member.name,
        sender_role=test_user_member.role.value,
        message_type="RECEIPT",
        content="Test receipt upload",
        attachment_id=test_upload.id,
        status=MessageStatus.PENDING.value,
        public_code="CF-20261004-TEST001"
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# ============================================================================
# Vision Result Fixtures
# ============================================================================

@pytest.fixture
def vision_success() -> VisionResult:
    """Standard successful vision extraction."""
    return VisionResult(
        transaction_code="FT26277123456789",
        amount=500000,
        sender_name="NGUYEN VAN A",
        bank_name="Vietcombank",
        transaction_time="2026-10-04T10:30:00Z",
        confidence=0.95,
        raw_text="Mock receipt text",
        needs_human_review=False
    )


@pytest.fixture
def vision_low_confidence() -> VisionResult:
    """Low confidence vision extraction."""
    return VisionResult(
        transaction_code="FT26277123456789",
        amount=500000,
        sender_name="NGUYEN VAN A",
        bank_name="Vietcombank",
        transaction_time="2026-10-04T10:30:00Z",
        confidence=0.5,
        raw_text="Unclear receipt",
        needs_human_review=True
    )


@pytest.fixture
def vision_missing_fields() -> VisionResult:
    """Vision extraction with missing required fields."""
    return VisionResult(
        transaction_code=None,
        amount=None,
        sender_name="NGUYEN VAN A",
        bank_name="Vietcombank",
        transaction_time="2026-10-04T10:30:00Z",
        confidence=0.6,
        raw_text="Partial receipt",
        needs_human_review=True
    )


@pytest.fixture
def vision_timeout() -> VisionResult:
    """Vision extraction timeout."""
    return VisionResult(
        error="Ollama request timeout",
        needs_human_review=True
    )


@pytest.fixture
def vision_connection_refused() -> VisionResult:
    """Vision extraction connection refused."""
    return VisionResult(
        error="Connection refused",
        needs_human_review=True
    )


# ============================================================================
# Auth Helpers
# ============================================================================

from app.core.security import create_access_token


def get_auth_headers(user_id: str, role: str = "MEMBER") -> dict:
    """Get authorization headers for a user with proper JWT token."""
    token = create_access_token(subject=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def get_owner_headers() -> dict:
    return get_auth_headers("owner-1", "OWNER_TREASURER")


def get_moderator_headers() -> dict:
    return get_auth_headers("moderator-1", "MODERATOR")


def get_member_headers() -> dict:
    return get_auth_headers("member-1", "MEMBER")


def get_public_headers() -> dict:
    return get_auth_headers("public-1", "PUBLIC")


def get_invalid_headers() -> dict:
    return {"Authorization": "Bearer mock-token-invalid"}


# ============================================================================
# Test Utilities
# ============================================================================

def create_test_message(db: Session, upload_id: str, status: str = MessageStatus.PENDING.value) -> Message:
    """Create a test message with given upload."""
    message = Message(
        conversation_id="conv-test",
        sender_id="member-1",
        sender_name="Test Member",
        sender_role="MEMBER",
        message_type="RECEIPT",
        content="Test receipt",
        attachment_id=upload_id,
        status=status,
        public_code=f"CF-20261004-TEST-{upload_id[:8]}"
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def create_test_extraction(
    db: Session,
    upload_id: str,
    bank_account_id: str,
    confidence: float = 0.95,
    transaction_code: str = "FT26277123456789",
    amount: int = 500000
) -> ExtractedTransaction:
    """Create a test extraction."""
    extraction = ExtractedTransaction(
        upload_id=upload_id,
        transaction_code=transaction_code,
        amount=Decimal(str(amount)),
        sender_name="NGUYEN VAN A",
        bank_name="Vietcombank",
        bank_account_id=bank_account_id,
        transaction_time=datetime.now(timezone.utc),
        confidence=Decimal(str(confidence)),
        status=UploadStatus.PROCESSING,
        currency="VND"
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction