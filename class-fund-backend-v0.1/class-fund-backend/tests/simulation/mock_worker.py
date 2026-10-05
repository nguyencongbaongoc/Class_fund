"""Mock Worker Simulator for simulation testing."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    Message, MessageStatus, Transaction, Upload, UploadStatus, WorkerStatus
)
from app.services.ledger import verify_and_post_from_ai, ProcessingResult

from tests.simulation.config import get_simulation_config, WorkerState

logger = logging.getLogger(__name__)


@dataclass
class WorkerSimulator:
    """Test-only worker simulator with controlled lifecycle."""
    
    worker_id: str = "test-worker"
    database_url: str = "sqlite+pysqlite:///:memory:"
    lease_duration_seconds: int = 300
    Session: Any = None
    
    def __post_init__(self):
        self.sim_config = get_simulation_config()
        self.sim_config.worker_id = self.worker_id
        self.sim_config.worker_lease_duration = self.lease_duration_seconds
    
    def startup(self, db: Session):
        """Initialize worker: reclaim stale leases, register status."""
        self.reclaim_stale_leases(db)
        self.upsert_worker_status(db, "online")
        self.sim_config.worker_state = WorkerState.ONLINE
        logger.info(f"Worker {self.worker_id} started (simulated)")
    
    def shutdown(self, db: Session):
        """Graceful shutdown."""
        self.upsert_worker_status(db, "offline")
        self.sim_config.worker_state = WorkerState.STOPPED
        logger.info(f"Worker {self.worker_id} stopped (simulated)")
    
    def reclaim_stale_leases(self, db: Session):
        """Reclaim messages stuck in processing from dead workers."""
        now = datetime.now(timezone.utc)
        stale_messages = db.execute(
            select(Message)
            .where(Message.status == MessageStatus.PROCESSING.value)
            .where(Message.lease_expires_at < now)
        ).scalars().all()
        
        for msg in stale_messages:
            msg.status = MessageStatus.PENDING.value
            msg.worker_id = None
            msg.claimed_at = None
            msg.lease_expires_at = None
        
        db.commit()
        logger.info("Reclaimed stale leases (simulated)")
    
    def upsert_worker_status(self, db: Session, status: str, current_job_id: Optional[str] = None):
        """Update worker status in database."""
        now = datetime.now(timezone.utc)
        db.execute(text("""
            INSERT INTO worker_status (worker_id, status, last_heartbeat, last_processed_at, current_job_id, worker_metadata)
            VALUES (:worker_id, :status, :now, :now, :job_id, '{}')
            ON CONFLICT (worker_id) DO UPDATE SET
                status = :status,
                last_heartbeat = :now,
                last_processed_at = COALESCE(:job_id, worker_status.last_processed_at),
                current_job_id = :job_id
        """), {
            "worker_id": self.worker_id,
            "status": status,
            "now": now,
            "job_id": current_job_id
        })
        db.commit()
        
        # Update simulation config
        self.sim_config.worker_state = WorkerState(status.upper()) if status.upper() in [s.value for s in WorkerState] else WorkerState.ONLINE
    
    def claim_next_message(self, db: Session) -> Optional[Message]:
        """Atomically claim the next pending message."""
        # Check for injected lease expiry
        if self.sim_config.inject_lease_expiry:
            return None
        
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=self.lease_duration_seconds)
        
        # For SQLite compatibility, use a simpler approach without FOR UPDATE SKIP LOCKED
        # Find the oldest pending message
        message = db.execute(
            select(Message)
            .where(Message.status == MessageStatus.PENDING.value)
            .order_by(Message.created_at)
            .limit(1)
        ).scalar_one_or_none()
        
        if message:
            # Update the message
            message.status = MessageStatus.PROCESSING.value
            message.worker_id = self.worker_id
            message.claimed_at = now
            message.lease_expires_at = lease_expires
            db.commit()
            
            self.sim_config.claimed_messages[message.id] = now
            self.sim_config.message_leases[message.id] = lease_expires
            return message
        return None
    
    def process_message(self, db: Session, message: Message):
        """Process a single message through the AI pipeline."""
        # Refresh message state
        db.expire(message)
        if message.status == MessageStatus.RECALLED.value:
            logger.info(f"Message {message.id} was recalled, skipping")
            self.recall_message(db, message)
            return
        
        # Check for injected worker crash - raise exception for testing (don't catch)
        if self.sim_config.inject_worker_crash:
            self.sim_config.worker_state = WorkerState.OFFLINE
            raise Exception("Worker crashed (injected)")
        
        # Get the associated upload
        upload = db.execute(select(Upload).where(Upload.id == message.attachment_id)).scalar_one_or_none()
        if not upload:
            self.fail_message(db, message, "No upload attached")
            return
        
        # Get or create extraction
        extraction = db.execute(
            select(ExtractedTransaction).where(ExtractedTransaction.upload_id == upload.id)
        ).scalar_one_or_none()
        
        if not extraction:
            self.fail_message(db, message, "No extraction found")
            return
        
        # Get default account
        account = db.execute(
            select(Account).where(Account.active.is_(True)).order_by(Account.created_at)
        ).scalars().first()
        if not account:
            self.fail_message(db, message, "No active fund account")
            return
        
        # Generate idempotency key
        import hashlib
        payload = f"{extraction.transaction_code}|{extraction.amount}|{extraction.bank_account_id}"
        content_version = hashlib.sha256(payload.encode()).hexdigest()[:8]
        idempotency_key = f"msg_{message.id}_v{content_version}"
        
        # Check for injected crash after external call - raise exception for testing (don't catch)
        if self.sim_config.worker_crash_after_external:
            # Process but don't complete
            result = verify_and_post_from_ai(
                db, upload, extraction, account=account, actor_id=None,
                idempotency_key=idempotency_key,
                message_id=message.id,
                logical_operation_id=f"msg_{message.id}",
                attempt_id=f"attempt_{message.retry_count + 1}"
            )
            # Crash before marking complete
            self.sim_config.worker_state = WorkerState.OFFLINE
            raise Exception("Worker crashed after external call (injected)")
        
        # Process through AI gatekeeper
        result = verify_and_post_from_ai(
            db, upload, extraction, account=account, actor_id=None,
            idempotency_key=idempotency_key,
            message_id=message.id,
            logical_operation_id=f"msg_{message.id}",
            attempt_id=f"attempt_{message.retry_count + 1}"
        )
        
        if result.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE):
            self.complete_message(db, message, result)
        elif result.status == ProcessingResult.NEEDS_HUMAN_REVIEW:
            self.await_review(db, message, result)
        elif result.status == ProcessingResult.RECALLED:
            self.recall_message(db, message)
        else:
            self.fail_message(db, message, result.error_message or "Unknown error", result.status)
        
        self.upsert_worker_status(db, "online")
    
    def complete_message(self, db: Session, message: Message, result):
        """Mark message as successfully processed."""
        msg = db.get(Message, message.id)
        if msg:
            msg.status = MessageStatus.POSTED.value
            msg.processed_at = datetime.now(timezone.utc)
            msg.transaction_id = result.transaction.id if result.transaction else None
            msg.worker_id = None
            msg.claimed_at = None
            msg.lease_expires_at = None
            db.commit()
        
        self.sim_config.claimed_messages.pop(message.id, None)
        self.sim_config.message_leases.pop(message.id, None)
        logger.info(f"Message {message.id} completed (simulated)")
    
    def await_review(self, db: Session, message: Message, result):
        """Mark message as awaiting human review."""
        msg = db.get(Message, message.id)
        if msg:
            msg.status = MessageStatus.AWAITING_REVIEW.value
            msg.processed_at = datetime.now(timezone.utc)
            msg.error_message = result.error_message
            msg.worker_id = None
            msg.claimed_at = None
            msg.lease_expires_at = None
            db.commit()
        
        self.sim_config.claimed_messages.pop(message.id, None)
        self.sim_config.message_leases.pop(message.id, None)
        logger.info(f"Message {message.id} awaiting review (simulated)")
    
    def fail_message(self, db: Session, message: Message, error: str, status: ProcessingResult = ProcessingResult.FAILED):
        """Mark message as failed with retry logic."""
        msg = db.get(Message, message.id)
        if msg:
            msg.retry_count += 1
            msg.error_message = error
            msg.worker_id = None
            msg.claimed_at = None
            msg.lease_expires_at = None
            
            if msg.retry_count >= 3:
                msg.status = MessageStatus.FAILED.value
                msg.processed_at = datetime.now(timezone.utc)
            else:
                delay = 60 * (2 ** (msg.retry_count - 1))
                msg.status = MessageStatus.PENDING.value
                msg.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            db.commit()
        
        self.sim_config.claimed_messages.pop(message.id, None)
        self.sim_config.message_leases.pop(message.id, None)
        logger.info(f"Message {message.id} failed: {error} (retry {msg.retry_count if msg else 'N/A'})")
    
    def recall_message(self, db: Session, message: Message):
        """Handle message recall."""
        msg = db.get(Message, message.id)
        if msg:
            msg.status = MessageStatus.RECALLED.value
            msg.processed_at = datetime.now(timezone.utc)
            msg.worker_id = None
            msg.claimed_at = None
            msg.lease_expires_at = None
            db.commit()
        
        self.sim_config.claimed_messages.pop(message.id, None)
        self.sim_config.message_leases.pop(message.id, None)
        logger.info(f"Message {message.id} recalled (simulated)")
    
    def handle_error(self, db: Session, message: Message, error: Exception):
        """Handle unexpected errors."""
        logger.error(f"Error processing message {message.id}: {error}")
        self.fail_message(db, message, str(error), ProcessingResult.RETRYABLE)
    
    def heartbeat(self, db: Session):
        """Update worker heartbeat."""
        self.upsert_worker_status(db, "online")
    
    def crash(self, db: Session):
        """Simulate worker crash."""
        self.sim_config.worker_state = WorkerState.OFFLINE
        self.upsert_worker_status(db, "offline")
        logger.warning(f"Worker {self.worker_id} crashed (simulated)")
    
    def recover(self, db: Session):
        """Simulate worker recovery after crash."""
        self.reclaim_stale_leases(db)
        self.upsert_worker_status(db, "online")
        self.sim_config.worker_state = WorkerState.RECOVERING
        logger.info(f"Worker {self.worker_id} recovering (simulated)")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        return {
            "worker_id": self.worker_id,
            "state": self.sim_config.worker_state.value,
            "claimed_messages": len(self.sim_config.claimed_messages),
            "active_leases": len(self.sim_config.message_leases)
        }


def create_test_worker(db: Session, worker_id: str = "test-worker") -> WorkerSimulator:
    """Create and start a test worker."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use the same session factory as the test
    engine = db.get_bind()
    Session = sessionmaker(bind=engine)
    
    worker = WorkerSimulator(
        worker_id=worker_id,
        database_url="",  # Not used directly
        Session=Session
    )
    worker.startup(db)
    return worker


def simulate_worker_lifecycle(
    db: Session,
    message_count: int = 1,
    crash_after: int = -1,
    fail_count: int = 0
) -> List[Dict[str, Any]]:
    """
    Simulate a complete worker lifecycle.
    
    Args:
        db: Database session
        message_count: Number of messages to process
        crash_after: Crash after N messages (-1 = never)
        fail_count: Number of messages to fail before success
    
    Returns:
        List of processing results
    """
    sim_config = get_simulation_config()
    sim_config.reset()  # Ensure clean state
    worker = create_test_worker(db)
    results = []
    
    for i in range(message_count):
        if crash_after >= 0 and i == crash_after:
            worker.sim_config.inject_worker_crash = True
        else:
            worker.sim_config.inject_worker_crash = False
        
        message = worker.claim_next_message(db)
        if not message:
            results.append({"status": "NO_MESSAGES", "message_id": None})
            break
        
        worker.process_message(db, message)
        
        # Check result
        db.expire(message)
        results.append({
            "status": message.status,
            "message_id": message.id,
            "transaction_id": message.transaction_id,
            "error": message.error_message
        })
        
        # Simulate heartbeat
        worker.heartbeat(db)
    
    worker.shutdown(db)
    sim_config.reset()
    return results