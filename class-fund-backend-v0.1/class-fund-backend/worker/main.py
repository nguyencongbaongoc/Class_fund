"""Supabase-backed persistent worker for message processing."""
from __future__ import annotations

import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    Message, MessageStatus, Transaction, Upload, UploadStatus
)
from app.services.ledger import verify_and_post_from_ai, ProcessingResult


class Worker:
    def __init__(self, worker_id: str, database_url: str, lease_duration_seconds: int = 300):
        self.worker_id = worker_id
        self.database_url = database_url
        self.lease_duration_seconds = lease_duration_seconds
        self.running = False
        self.engine = create_engine(database_url, future=True, pool_size=5, max_overflow=10)
        self.Session = sessionmaker(bind=self.engine)
        
    def startup(self):
        """Initialize worker: reclaim stale leases, register status."""
        self.reclaim_stale_leases()
        self.upsert_worker_status("online")
        print(f"Worker {self.worker_id} started")
        
    def shutdown(self):
        """Graceful shutdown."""
        self.running = False
        self.upsert_worker_status("offline")
        print(f"Worker {self.worker_id} stopped")
        
    def reclaim_stale_leases(self):
        """Reclaim messages stuck in processing from dead workers."""
        with self.Session() as db:
            db.execute(text("""
                UPDATE messages
                SET status = 'pending',
                    worker_id = NULL,
                    claimed_at = NULL,
                    lease_expires_at = NULL
                WHERE status = 'processing'
                AND lease_expires_at < :now
            """), {"now": datetime.now(timezone.utc)})
            db.commit()
            
    def upsert_worker_status(self, status: str, current_job_id: Optional[str] = None):
        """Update worker status in database."""
        with self.Session() as db:
            db.execute(text("""
                INSERT INTO worker_status (worker_id, status, last_heartbeat, last_processed_at, current_job_id, metadata)
                VALUES (:worker_id, :status, :now, :now, :job_id, '{}')
                ON CONFLICT (worker_id) DO UPDATE SET
                    status = :status,
                    last_heartbeat = :now,
                    last_processed_at = COALESCE(:job_id, worker_status.last_processed_at),
                    current_job_id = :job_id
            """), {
                "worker_id": self.worker_id,
                "status": status,
                "now": datetime.now(timezone.utc),
                "job_id": current_job_id
            })
            db.commit()
            
    def claim_next_message(self) -> Optional[Message]:
        """Atomically claim the next pending message using FOR UPDATE SKIP LOCKED."""
        with self.Session() as db:
            now = datetime.now(timezone.utc)
            lease_expires = now.replace(second=now.second + self.lease_duration_seconds)
            
            # Atomic claim with lease
            result = db.execute(text("""
                UPDATE messages
                SET status = 'processing',
                    worker_id = :worker_id,
                    claimed_at = :now,
                    lease_expires_at = :lease_expires
                WHERE id = (
                    SELECT id FROM messages
                    WHERE status = 'pending'
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
            """), {
                "worker_id": self.worker_id,
                "now": now,
                "lease_expires": lease_expires
            }).mappings().first()
            
            if result:
                return db.get(Message, result["id"])
            return None
            
    def process_message(self, message: Message):
        """Process a single message through the AI pipeline."""
        try:
            # Check if message was recalled before processing
            db = self.Session()
            db.expire(message)
            if message.status == MessageStatus.RECALLED.value:
                print(f"Message {message.id} was recalled, skipping")
                return
                
            # Get the associated upload
            upload = db.execute(select(Upload).where(Upload.id == message.attachment_id)).scalar_one_or_none()
            if not upload:
                self.fail_message(message, "No upload attached")
                return
                
            # Get or create extraction
            extraction = db.execute(
                select(ExtractedTransaction).where(ExtractedTransaction.upload_id == upload.id)
            ).scalar_one_or_none()
            
            if not extraction:
                self.fail_message(message, "No extraction found")
                return
                
            # Get default account
            account = db.execute(
                select(Account).where(Account.active.is_(True)).order_by(Account.created_at)
            ).scalars().first()
            if not account:
                self.fail_message(message, "No active fund account")
                return
                
            # Generate idempotency key (stable: msg_{message_id}_v{content_version})
            # Content version based on financial payload hash
            import hashlib
            payload = f"{extraction.transaction_code}|{extraction.amount}|{extraction.bank_account_id}"
            content_version = hashlib.sha256(payload.encode()).hexdigest()[:8]
            idempotency_key = f"msg_{message.id}_v{content_version}"
            
            # Process through AI gatekeeper
            result = verify_and_post_from_ai(
                db, upload, extraction, account=account, actor_id=None,
                idempotency_key=idempotency_key,
                message_id=message.id,
                logical_operation_id=f"msg_{message.id}",
                attempt_id=f"attempt_{message.retry_count + 1}"
            )
            
            if result.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE):
                self.complete_message(message, result)
            elif result.status == ProcessingResult.NEEDS_HUMAN_REVIEW:
                self.await_review(message, result)
            elif result.status == ProcessingResult.RECALLED:
                self.recall_message(message)
            else:
                self.fail_message(message, result.error_message or "Unknown error", result.status)
                
        except Exception as e:
            self.handle_error(message, e)
        finally:
            db.close()
            
    def complete_message(self, message: Message, result):
        """Mark message as successfully processed."""
        with self.Session() as db:
            msg = db.get(Message, message.id)
            if msg:
                msg.status = MessageStatus.POSTED.value
                msg.processed_at = datetime.now(timezone.utc)
                msg.transaction_id = result.transaction.id if result.transaction else None
                msg.worker_id = None
                msg.claimed_at = None
                msg.lease_expires_at = None
                db.commit()
            self.upsert_worker_status("online")
            
    def await_review(self, message: Message, result):
        """Mark message as awaiting human review."""
        with self.Session() as db:
            msg = db.get(Message, message.id)
            if msg:
                msg.status = MessageStatus.AWAITING_REVIEW.value
                msg.processed_at = datetime.now(timezone.utc)
                msg.error_message = result.error_message
                msg.worker_id = None
                msg.claimed_at = None
                msg.lease_expires_at = None
                db.commit()
            self.upsert_worker_status("online")
            
    def fail_message(self, message: Message, error: str, status: ProcessingResult = ProcessingResult.FAILED):
        """Mark message as failed with retry logic."""
        with self.Session() as db:
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
                    # Exponential backoff: 60s, 120s, 240s
                    delay = 60 * (2 ** (msg.retry_count - 1))
                    msg.status = MessageStatus.PENDING.value
                    # Schedule retry by setting a future lease expiry
                    from datetime import timedelta
                    msg.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                db.commit()
            self.upsert_worker_status("online")
            
    def recall_message(self, message: Message):
        """Handle message recall (message was recalled before/during processing)."""
        with self.Session() as db:
            msg = db.get(Message, message.id)
            if msg:
                msg.status = MessageStatus.RECALLED.value
                msg.processed_at = datetime.now(timezone.utc)
                msg.worker_id = None
                msg.claimed_at = None
                msg.lease_expires_at = None
                db.commit()
            self.upsert_worker_status("online")
            
    def handle_error(self, message: Message, error: Exception):
        """Handle unexpected errors."""
        print(f"Error processing message {message.id}: {error}")
        self.fail_message(message, str(error), ProcessingResult.RETRYABLE)
        
    def run(self):
        """Main processing loop."""
        self.running = True
        self.startup()
        
        # Handle graceful shutdown
        def signal_handler(signum, frame):
            print(f"Received signal {signum}, shutting down...")
            self.shutdown()
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while self.running:
            try:
                message = self.claim_next_message()
                if message:
                    self.upsert_worker_status("online", current_job_id=message.id)
                    self.process_message(message)
                else:
                    # No messages, wait before polling again
                    time.sleep(5)
            except Exception as e:
                print(f"Worker error: {e}")
                time.sleep(10)  # Back off on errors


def main():
    settings = get_settings()
    worker_id = os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")
    database_url = os.getenv("DATABASE_URL", settings.database_url)
    lease_duration = int(os.getenv("LEASE_DURATION", "300"))
    
    worker = Worker(worker_id, database_url, lease_duration)
    worker.run()


if __name__ == "__main__":
    main()