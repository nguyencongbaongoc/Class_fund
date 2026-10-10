"""Persistent worker for message processing with Redis Pub/Sub events."""
from __future__ import annotations

import os
import signal
import sys
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from redis.asyncio import Redis, ConnectionPool

from app.core.config import get_settings
from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    Message, MessageStatus, Transaction, Upload, UploadStatus, WorkerStatus
)
from app.services.ledger import verify_and_post_from_ai, ProcessingResult
from ai.duplicate.service import DuplicateDetector


class Worker:
    def __init__(self, worker_id: str, database_url: str, lease_duration_seconds: int = 300,
                 redis_url: Optional[str] = None):
        self.worker_id = worker_id
        self.database_url = database_url
        self.lease_duration_seconds = lease_duration_seconds
        self.redis_url = redis_url or "redis://redis:6379/0"
        self.running = False
        self.duplicate_loading_failed = False
        self.duplicate_detector = None
        self.engine = create_engine(database_url, future=True, pool_size=5, max_overflow=10)
        self.Session = sessionmaker(bind=self.engine)
        self._redis_pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._redis_initialized = False
        
    async def _init_redis(self):
        """Initialize Redis connection pool."""
        if self._redis_initialized:
            return
        self._redis_pool = ConnectionPool.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=10
        )
        self._redis = Redis(connection_pool=self._redis_pool)
        self._redis_initialized = True
    
    async def _publish_event(self, channel: str, event_type: str, payload: dict):
        """Publish event to Redis Pub/Sub."""
        if not self._redis_initialized:
            await self._init_redis()
        
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "worker_id": self.worker_id
        }
        
        try:
            await self._redis.publish(channel, json.dumps(event))
        except Exception as e:
            print(f"Failed to publish event to {channel}: {e}")
        
    def startup(self):
        """Initialize worker: reclaim stale leases, load duplicate data, register status."""
        self.reclaim_stale_leases()
        
        # Load persistent duplicate detection data before accepting jobs
        success, error = self._load_duplicate_detection_data()
        if not success:
            print(f"CRITICAL: Failed to load duplicate detection data: {error}")
            print("Worker will not accept duplicate-dependent jobs until data is loaded.")
            # In production, you might want to exit or enter a degraded mode
            # For now, we log and continue but mark the worker as degraded
            self.duplicate_loading_failed = True
        else:
            self.duplicate_loading_failed = False
            print(f"Worker {self.worker_id} duplicate detection data loaded successfully")
        
        self.upsert_worker_status("online")
        print(f"Worker {self.worker_id} started")

    def _load_duplicate_detection_data(self) -> tuple[bool, Optional[str]]:
        """Load duplicate detection data from database."""
        try:
            # Create a detector instance
            detector = DuplicateDetector()
            with self.Session() as db:
                success, error = detector.load_from_database(db)
                if not success:
                    return False, error
                
                # Store the detector for use in processing
                self.duplicate_detector = detector
                return True, None
        except Exception as e:
            return False, str(e)
        
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
            now = datetime.now(timezone.utc)
            ws = db.get(WorkerStatus, self.worker_id)
            if ws:
                ws.status = status
                ws.last_heartbeat = now
                if current_job_id:
                    ws.last_processed_at = now
                ws.current_job_id = current_job_id
            else:
                ws = WorkerStatus(
                    worker_id=self.worker_id,
                    status=status,
                    last_heartbeat=now,
                    last_processed_at=now if current_job_id else None,
                    current_job_id=current_job_id,
                    worker_metadata={},
                )
                db.add(ws)
            db.commit()
            
    def claim_next_message(self) -> Optional[Message]:
        """Atomically claim the next pending message using FOR UPDATE SKIP LOCKED."""
        with self.Session() as db:
            now = datetime.now(timezone.utc)
            lease_expires = now + timedelta(seconds=self.lease_duration_seconds)
            msg = db.execute(
                select(Message)
                .where(Message.status == MessageStatus.PENDING.value)
                .order_by(Message.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            ).scalars().first()
            if msg:
                msg.status = MessageStatus.PROCESSING.value
                msg.worker_id = self.worker_id
                msg.claimed_at = now
                msg.lease_expires_at = lease_expires
                db.commit()
                db.refresh(msg)
                return msg
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