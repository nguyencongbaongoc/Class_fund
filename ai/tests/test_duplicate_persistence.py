"""Tests for duplicate detection persistence."""
import hashlib
import tempfile
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai.duplicate.service import DuplicateDetector
from ai.contracts import VerificationResult, VerificationStatus
from ai.ocr.service import compute_perceptual_hash

# Import the backend models and create test database
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "class-fund-backend-v0.1" / "class-fund-backend"))

from app.models.models import Upload, ExtractedTransaction, UploadStatus
from app.db.base import Base


@pytest.fixture
def test_db():
    """Create a temporary SQLite database for testing."""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    
    yield SessionLocal
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def sample_image_bytes():
    """Create a simple test image."""
    from PIL import Image
    import io
    
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


class TestDuplicateDetectorPersistence:
    """Tests for DuplicateDetector database persistence."""
    
    def test_load_from_empty_database(self, test_db):
        """Test loading from an empty database."""
        detector = DuplicateDetector()
        
        with test_db() as db:
            success, error = detector.load_from_database(db)
            
        assert success is True
        assert error is None
        assert len(detector.file_hash_detector.seen_hashes) == 0
        assert len(detector.perceptual_hash_detector.seen_hashes) == 0
        assert len(detector.transaction_identity_detector.seen_identities) == 0
    
    def test_load_persisted_file_hash(self, test_db, sample_image_bytes):
        """Test loading file hashes from database."""
        file_hash = hashlib.sha256(sample_image_bytes).hexdigest()
        
        # Create test upload with file hash
        with test_db() as db:
            upload = Upload(
                file_hash=file_hash,
                original_filename="test.png",
                storage_path="/tmp/test.png",
                uploader_name="Test User",
                status=UploadStatus.PENDING
            )
            db.add(upload)
            db.commit()
        
        # Load with new detector
        detector = DuplicateDetector()
        with test_db() as db:
            success, error = detector.load_from_database(db)
        
        assert success is True
        assert error is None
        assert file_hash in detector.file_hash_detector.seen_hashes
    
    def test_load_persisted_perceptual_hash(self, test_db, sample_image_bytes):
        """Test loading perceptual hashes from database."""
        phash = compute_perceptual_hash(sample_image_bytes)
        
        # Create test upload with perceptual hash
        with test_db() as db:
            upload = Upload(
                file_hash=hashlib.sha256(sample_image_bytes).hexdigest(),
                perceptual_hash=phash,
                original_filename="test.png",
                storage_path="/tmp/test.png",
                uploader_name="Test User",
                status=UploadStatus.PENDING
            )
            db.add(upload)
            db.commit()
            upload_id = upload.id
        
        # Load with new detector
        detector = DuplicateDetector()
        with test_db() as db:
            success, error = detector.load_from_database(db)
        
        assert success is True
        assert error is None
        assert phash in detector.perceptual_hash_detector.seen_hashes
        assert detector.perceptual_hash_detector.seen_hashes[phash] == upload_id
    
    def test_load_persisted_transaction_identity(self, test_db):
        """Test loading transaction identities from database."""
        # Create test extraction with transaction code
        with test_db() as db:
            upload = Upload(
                file_hash="dummy_hash",
                original_filename="test.png",
                storage_path="/tmp/test.png",
                uploader_name="Test User",
                status=UploadStatus.PENDING
            )
            db.add(upload)
            db.commit()
            upload_id = upload.id
            
            extraction = ExtractedTransaction(
                upload_id=upload_id,
                transaction_code="FT123456789",
                bank_name="Vietcombank",
                amount=100000,
                status=UploadStatus.PROCESSING
            )
            db.add(extraction)
            db.commit()
        
        # Load with new detector
        detector = DuplicateDetector()
        with test_db() as db:
            success, error = detector.load_from_database(db)
        
        assert success is True
        assert error is None
        assert "VIETCOMBANK|FT123456789" in detector.transaction_identity_detector.seen_identities
        assert detector.transaction_identity_detector.seen_identities["VIETCOMBANK|FT123456789"] == upload_id
    
    def test_reload_twice_no_duplicates(self, test_db, sample_image_bytes):
        """Test that loading twice doesn't create duplicate in-memory entries."""
        file_hash = hashlib.sha256(sample_image_bytes).hexdigest()
        
        with test_db() as db:
            upload = Upload(
                file_hash=file_hash,
                original_filename="test.png",
                storage_path="/tmp/test.png",
                uploader_name="Test User",
                status=UploadStatus.PENDING
            )
            db.add(upload)
            db.commit()
        
        detector = DuplicateDetector()
        with test_db() as db:
            detector.load_from_database(db)
        
        initial_count = len(detector.file_hash_detector.seen_hashes)
        
        # Load again
        with test_db() as db:
            detector.load_from_database(db)
        
        # Count should be the same
        assert len(detector.file_hash_detector.seen_hashes) == initial_count
    
    def test_persist_duplicate_data(self, test_db, sample_image_bytes):
        """Test persisting duplicate detection data to database."""
        from ai.duplicate.service import DuplicateDetector
        
        detector = DuplicateDetector()
        
        with test_db() as db:
            # Create upload first
            upload = Upload(
                file_hash="initial_hash",
                original_filename="test.png",
                storage_path="/tmp/test.png",
                uploader_name="Test User",
                status=UploadStatus.PENDING
            )
            db.add(upload)
            db.commit()
            upload_id = upload.id
            
            # Create extraction
            extraction = ExtractedTransaction(
                upload_id=upload_id,
                transaction_code="FT123456789",
                bank_name="Vietcombank",
                amount=100000,
                status=UploadStatus.PROCESSING
            )
            db.add(extraction)
            db.commit()
            
            # Create a verification result
            verification = VerificationResult(
                upload_id=upload_id,
                transaction_code="FT123456789",
                amount=100000,
                sender_name="Test Sender",
                bank_name="Vietcombank",
                transaction_time=None,
                confidence=0.95,
                status=VerificationStatus.VERIFIED,
            )
            
            # Persist duplicate data
            detector.persist_duplicate_data(db, sample_image_bytes, verification)
            db.commit()
            
            from sqlalchemy import select
            # Verify the upload was updated in the database
            updated_upload = db.execute(
                select(Upload).where(Upload.id == upload_id)
            ).scalar_one()
            new_file_hash = hashlib.sha256(sample_image_bytes).hexdigest()
            assert updated_upload.file_hash == new_file_hash, f"Expected {new_file_hash}, got {updated_upload.file_hash}"
            assert updated_upload.perceptual_hash is not None
        
        # Reload and verify with new detector
        new_detector = DuplicateDetector()
        with test_db() as db:
            success, error = new_detector.load_from_database(db)
        
        assert success is True
        
        # Check file hash was updated
        new_file_hash = hashlib.sha256(sample_image_bytes).hexdigest()
        assert new_file_hash in new_detector.file_hash_detector.seen_hashes
        
        # Check perceptual hash was stored
        phash = compute_perceptual_hash(sample_image_bytes)
        assert phash in new_detector.perceptual_hash_detector.seen_hashes
        
        # Check transaction identity
        assert "VIETCOMBANK|FT123456789" in new_detector.transaction_identity_detector.seen_identities
    
    def test_database_failure_handling(self, test_db):
        """Test handling of database failures during load."""
        detector = DuplicateDetector()
        
        # Create a mock db that raises an exception
        class MockDB:
            def execute(self, *args, **kwargs):
                raise Exception("Database connection failed")
        
        mock_db = MockDB()
        success, error = detector.load_from_database(mock_db)
        
        assert success is False
        assert error is not None
        assert "Failed to load duplicate detection data" in error
    
    def test_detect_duplicate_after_restart(self, test_db, sample_image_bytes):
        """Test that a duplicate can be detected after process restart."""
        # First session: create upload and extract
        file_hash = hashlib.sha256(sample_image_bytes).hexdigest()
        phash = compute_perceptual_hash(sample_image_bytes)
        
        with test_db() as db:
            upload = Upload(
                file_hash=file_hash,
                perceptual_hash=phash,
                original_filename="test.png",
                storage_path="/tmp/test.png",
                uploader_name="Test User",
                status=UploadStatus.VERIFIED
            )
            db.add(upload)
            db.commit()
            upload_id = upload.id
            
            extraction = ExtractedTransaction(
                upload_id=upload_id,
                transaction_code="FT123456789",
                bank_name="Vietcombank",
                amount=100000,
                status=UploadStatus.VERIFIED
            )
            db.add(extraction)
            db.commit()
        
        # Simulate process restart: new detector loads from database
        detector1 = DuplicateDetector()
        with test_db() as db:
            success, error = detector1.load_from_database(db)
        assert success is True
        
        # Verify duplicate detection works
        result = detector1.perceptual_hash_detector.check(sample_image_bytes)
        assert result.is_duplicate is True
        assert result.layer == "perceptual_hash"
        assert result.matched_upload_id == upload_id
        
        # Also test file hash duplicate
        result2 = detector1.file_hash_detector.check(sample_image_bytes)
        assert result2.is_duplicate is True
        assert result2.layer == "file_hash"
    
    def test_worker_refuses_jobs_when_loading_fails(self, test_db):
        """Test that worker handles loading failure appropriately."""
        # This test verifies the logic in worker startup
        # We can't fully test the worker without a real database,
        # but we can verify the detector returns proper failure
        
        detector = DuplicateDetector()
        
        # Test with a mock db that raises an exception
        class MockDB:
            def execute(self, *args, **kwargs):
                raise Exception("Database connection failed")
        
        mock_db = MockDB()
        success, error = detector.load_from_database(mock_db)
        
        assert success is False
        assert error is not None
        assert "Failed to load duplicate detection data" in error
        
        # The worker should detect this and set duplicate_loading_failed = True
        # This is tested in the worker integration test


# Need to import hashlib and VerificationStatus
import hashlib
from ai.contracts import VerificationStatus
from sqlalchemy.orm import sessionmaker