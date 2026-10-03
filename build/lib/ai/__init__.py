from __future__ import annotations

from ai.contracts import (
    AmountExtraction,
    BankExtraction,
    DateTimeExtraction,
    DuplicateCheckResult,
    ExtractionEvidence,
    OCRResult,
    ProcessingJob,
    RiskFlag,
    SenderExtraction,
    StudentMatch,
    TransactionCodeExtraction,
    UploadMetadata,
    VerificationResult,
    VerificationStatus,
)
from ai.duplicate.service import (
    DuplicateDetector,
    FileHashDetector,
    PerceptualHashDetector,
    TransactionIdentityDetector,
)
from ai.extraction.service import (
    AmountExtractor,
    BankExtractor,
    DateTimeExtractor,
    ExtractionService,
    SenderExtractor,
    TransactionCodeExtractor,
)
from ai.matching.service import MatchingService, NameNormalizer, StudentMatcher, StudentRecord
from ai.ocr.service import (
    OCRService,
    Preprocessor,
    TesseractEngine,
    compute_file_hash,
    compute_perceptual_hash,
)
from ai.verification.service import VerificationPolicy, VerificationService
from ai.worker.queue import (
    QueueConfig,
    VerificationWorker,
    create_celery_app,
    process_verification_task,
)

__version__ = "1.0.0"

__all__ = [
    "VerificationResult",
    "VerificationStatus",
    "ProcessingJob",
    "UploadMetadata",
    "AmountExtraction",
    "TransactionCodeExtraction",
    "SenderExtraction",
    "BankExtraction",
    "DateTimeExtraction",
    "OCRResult",
    "StudentMatch",
    "DuplicateCheckResult",
    "RiskFlag",
    "ExtractionEvidence",
    "OCRService",
    "Preprocessor",
    "TesseractEngine",
    "compute_file_hash",
    "compute_perceptual_hash",
    "ExtractionService",
    "AmountExtractor",
    "TransactionCodeExtractor",
    "SenderExtractor",
    "BankExtractor",
    "DateTimeExtractor",
    "MatchingService",
    "StudentMatcher",
    "StudentRecord",
    "NameNormalizer",
    "DuplicateDetector",
    "FileHashDetector",
    "PerceptualHashDetector",
    "TransactionIdentityDetector",
    "VerificationService",
    "VerificationPolicy",
    "VerificationWorker",
    "QueueConfig",
    "process_verification_task",
    "create_celery_app",
]
