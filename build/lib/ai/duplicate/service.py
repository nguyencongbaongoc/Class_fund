from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from ai.contracts import DuplicateCheckResult, VerificationResult


@dataclass
class DuplicateContext:
    file_hashes: set[str]
    perceptual_hashes: dict[str, str]
    transaction_identities: dict[str, str]


class FileHashDetector:
    def __init__(self) -> None:
        self.seen_hashes: set[str] = set()

    def check(self, image_bytes: bytes) -> DuplicateCheckResult:
        file_hash = hashlib.sha256(image_bytes).hexdigest()

        if file_hash in self.seen_hashes:
            return DuplicateCheckResult(
                is_duplicate=True,
                layer="file_hash",
                confidence=1.0,
                details={"hash": file_hash},
            )

        self.seen_hashes.add(file_hash)
        return DuplicateCheckResult(
            is_duplicate=False,
            layer="file_hash",
            confidence=1.0,
            details={"hash": file_hash},
        )

    def add_hash(self, file_hash: str) -> None:
        self.seen_hashes.add(file_hash)


class PerceptualHashDetector:
    def __init__(self, threshold: int = 10) -> None:
        self.threshold = threshold
        self.seen_hashes: dict[str, str] = {}

    def compute_phash(self, image_bytes: bytes) -> str:
        image = Image.open(BytesIO(image_bytes))
        image = image.convert("L").resize((32, 32), Image.Resampling.LANCZOS)
        pixels = np.array(image, dtype=np.float64)
        dct = cv2.dct(pixels)
        dct_low = dct[:8, :8]
        median = np.median(dct_low)
        hash_bits = (dct_low > median).flatten()
        hash_int = 0
        for bit in hash_bits:
            hash_int = (hash_int << 1) | int(bit)
        return f"{hash_int:016x}"

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        x = int(hash1, 16) ^ int(hash2, 16)
        return bin(x).count("1")

    def check(self, image_bytes: bytes) -> DuplicateCheckResult:
        phash = self.compute_phash(image_bytes)

        for existing_hash, upload_id in self.seen_hashes.items():
            distance = self.hamming_distance(phash, existing_hash)
            if distance <= self.threshold:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    layer="perceptual_hash",
                    confidence=1.0 - (distance / 64.0),
                    details={
                        "phash": phash,
                        "matched_phash": existing_hash,
                        "hamming_distance": distance,
                        "threshold": self.threshold,
                    },
                    matched_upload_id=upload_id,
                )

        self.seen_hashes[phash] = ""
        return DuplicateCheckResult(
            is_duplicate=False,
            layer="perceptual_hash",
            confidence=1.0,
            details={"phash": phash},
        )

    def add_hash(self, phash: str, upload_id: str) -> None:
        self.seen_hashes[phash] = upload_id


class TransactionIdentityDetector:
    def __init__(self) -> None:
        self.seen_identities: dict[str, str] = {}

    def _build_identity_key(self, verification: VerificationResult) -> str | None:
        if not verification.transaction_code:
            return None

        bank_context = verification.bank_name or "UNKNOWN"
        return f"{bank_context}|{verification.transaction_code}"

    def check(self, verification: VerificationResult) -> DuplicateCheckResult:
        identity_key = self._build_identity_key(verification)

        if not identity_key:
            return DuplicateCheckResult(
                is_duplicate=False,
                layer="transaction_identity",
                confidence=0.0,
                details={"reason": "missing_transaction_code"},
            )

        if identity_key in self.seen_identities:
            return DuplicateCheckResult(
                is_duplicate=True,
                layer="transaction_identity",
                confidence=1.0,
                details={
                    "identity_key": identity_key,
                    "transaction_code": verification.transaction_code,
                    "bank_name": verification.bank_name,
                },
                matched_upload_id=self.seen_identities[identity_key],
            )

        self.seen_identities[identity_key] = str(verification.upload_id)
        return DuplicateCheckResult(
            is_duplicate=False,
            layer="transaction_identity",
            confidence=1.0,
            details={"identity_key": identity_key},
        )

    def add_identity(self, verification: VerificationResult) -> None:
        identity_key = self._build_identity_key(verification)
        if identity_key:
            self.seen_identities[identity_key] = str(verification.upload_id)


class DuplicateDetector:
    def __init__(self, phash_threshold: int = 10) -> None:
        self.file_hash_detector = FileHashDetector()
        self.perceptual_hash_detector = PerceptualHashDetector(threshold=phash_threshold)
        self.transaction_identity_detector = TransactionIdentityDetector()

    def check_all(
        self,
        image_bytes: bytes,
        verification: VerificationResult,
    ) -> list[DuplicateCheckResult]:
        results = []

        file_hash_result = self.file_hash_detector.check(image_bytes)
        results.append(file_hash_result)

        phash_result = self.perceptual_hash_detector.check(image_bytes)
        results.append(phash_result)

        identity_result = self.transaction_identity_detector.check(verification)
        results.append(identity_result)

        return results

    def register(
        self,
        image_bytes: bytes,
        verification: VerificationResult,
    ) -> None:
        file_hash = hashlib.sha256(image_bytes).hexdigest()
        self.file_hash_detector.add_hash(file_hash)

        phash = self.perceptual_hash_detector.compute_phash(image_bytes)
        self.perceptual_hash_detector.add_hash(phash, str(verification.upload_id))

        self.transaction_identity_detector.add_identity(verification)

    def load_existing(
        self,
        file_hashes: set[str],
        perceptual_hashes: dict[str, str],
        transaction_identities: dict[str, str],
    ) -> None:
        self.file_hash_detector.seen_hashes.update(file_hashes)
        self.perceptual_hash_detector.seen_hashes.update(perceptual_hashes)
        self.transaction_identity_detector.seen_identities.update(transaction_identities)
