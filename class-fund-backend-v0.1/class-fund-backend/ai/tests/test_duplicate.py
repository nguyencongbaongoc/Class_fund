import hashlib
import uuid
from io import BytesIO

from PIL import Image

from ai.contracts import VerificationResult, VerificationStatus
from ai.duplicate.service import (
    DuplicateDetector,
    FileHashDetector,
    PerceptualHashDetector,
    TransactionIdentityDetector,
)


class TestFileHashDetector:
    def setup_method(self):
        self.detector = FileHashDetector()

    def test_same_file_detected(self):
        image_bytes = b"test image data"
        result1 = self.detector.check(image_bytes)
        assert result1.is_duplicate is False

        result2 = self.detector.check(image_bytes)
        assert result2.is_duplicate is True
        assert result2.layer == "file_hash"
        assert result2.confidence == 1.0

    def test_different_files_not_duplicate(self):
        result1 = self.detector.check(b"image 1")
        result2 = self.detector.check(b"image 2")
        assert result1.is_duplicate is False
        assert result2.is_duplicate is False

    def test_add_hash(self):
        file_hash = hashlib.sha256(b"test").hexdigest()
        self.detector.add_hash(file_hash)
        result = self.detector.check(b"test")
        assert result.is_duplicate is True


class TestPerceptualHashDetector:
    def setup_method(self):
        self.detector = PerceptualHashDetector(threshold=10)

    def create_test_image(self, color="red", size=(100, 100), pattern=False):
        image = Image.new("RGB", size, color=color)
        if pattern:
            # Add some pattern to make images distinct
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            for i in range(0, size[0], 10):
                draw.line([(i, 0), (i, size[1])], fill="black", width=1)
            for i in range(0, size[1], 10):
                draw.line([(0, i), (size[0], i)], fill="black", width=1)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_identical_images_detected(self):
        img_bytes = self.create_test_image("red")
        result1 = self.detector.check(img_bytes)
        assert result1.is_duplicate is False

        result2 = self.detector.check(img_bytes)
        assert result2.is_duplicate is True
        assert result2.layer == "perceptual_hash"
        assert result2.confidence > 0.9

    def test_resized_image_detected(self):
        img1 = self.create_test_image("blue", (200, 200))
        img2 = self.create_test_image("blue", (100, 100))

        result1 = self.detector.check(img1)
        assert result1.is_duplicate is False

        result2 = self.detector.check(img2)
        assert result2.is_duplicate is True

    def test_compressed_image_detected(self):
        img1 = self.create_test_image("green", (100, 100))
        buffer1 = BytesIO()
        Image.open(BytesIO(img1)).save(buffer1, format="JPEG", quality=90)
        img1_compressed = buffer1.getvalue()

        img2 = self.create_test_image("green", (100, 100))
        buffer2 = BytesIO()
        Image.open(BytesIO(img2)).save(buffer2, format="JPEG", quality=50)
        img2_compressed = buffer2.getvalue()

        result1 = self.detector.check(img1_compressed)
        assert result1.is_duplicate is False

        result2 = self.detector.check(img2_compressed)
        assert result2.is_duplicate is True

    def test_different_images_not_duplicate(self):
        img1 = self.create_test_image("red", pattern=True)
        img2 = self.create_test_image("blue", pattern=True)

        result1 = self.detector.check(img1)
        result2 = self.detector.check(img2)

        assert result1.is_duplicate is False
        assert result2.is_duplicate is False

    def test_add_hash(self):
        img_bytes = self.create_test_image("yellow")
        phash = self.detector.compute_phash(img_bytes)
        self.detector.add_hash(phash, "upload-123")

        result = self.detector.check(img_bytes)
        assert result.is_duplicate is True
        assert result.matched_upload_id == "upload-123"


class TestTransactionIdentityDetector:
    def setup_method(self):
        self.detector = TransactionIdentityDetector()

    def create_verification(self, transaction_code: str, bank_name: str, upload_id: str):
        # Generate a deterministic UUID from the upload_id string
        import hashlib
        uuid_bytes = hashlib.md5(upload_id.encode()).digest()[:16]
        # Set version to 4 (random)
        uuid_bytes = bytearray(uuid_bytes)
        uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x40
        uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
        return VerificationResult(
            upload_id=uuid.UUID(bytes=bytes(uuid_bytes)),
            transaction_code=transaction_code,
            amount=50000,
            bank_name=bank_name,
            confidence=0.9,
            status=VerificationStatus.VERIFIED,
        )

    def test_same_transaction_code_same_bank_detected(self):
        v1 = self.create_verification("FT123456789", "MB Bank", "upload-1")
        result1 = self.detector.check(v1)
        assert result1.is_duplicate is False

        v2 = self.create_verification("FT123456789", "MB Bank", "upload-2")
        result2 = self.detector.check(v2)
        assert result2.is_duplicate is True
        assert result2.layer == "transaction_identity"
        assert result2.confidence == 1.0
        # matched_upload_id is now a UUID string
        assert result2.matched_upload_id is not None
        import uuid
        uuid.UUID(result2.matched_upload_id)  # Should not raise

    def test_same_transaction_code_different_bank_not_duplicate(self):
        v1 = self.create_verification("FT123456789", "MB Bank", "upload-1")
        result1 = self.detector.check(v1)
        assert result1.is_duplicate is False

        v2 = self.create_verification("FT123456789", "Vietcombank", "upload-2")
        result2 = self.detector.check(v2)
        assert result2.is_duplicate is False

    def test_missing_transaction_code_not_duplicate(self):
        v1 = self.create_verification(None, "MB Bank", "upload-1")
        result1 = self.detector.check(v1)
        assert result1.is_duplicate is False
        assert result1.details.get("reason") == "missing_transaction_code"

    def test_add_identity(self):
        v1 = self.create_verification("FT123456789", "MB Bank", "upload-1")
        self.detector.add_identity(v1)

        v2 = self.create_verification("FT123456789", "MB Bank", "upload-2")
        result = self.detector.check(v2)
        assert result.is_duplicate is True


class TestDuplicateDetector:
    def setup_method(self):
        self.detector = DuplicateDetector(phash_threshold=10)

    def create_test_image(self, color="red"):
        image = Image.new("RGB", (100, 100), color=color)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def create_verification(self, transaction_code: str = None, bank_name: str = None, upload_id: str = "upload-1"):
        import hashlib
        uuid_bytes = hashlib.md5(upload_id.encode()).digest()[:16]
        uuid_bytes = bytearray(uuid_bytes)
        uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x40
        uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
        return VerificationResult(
            upload_id=uuid.UUID(bytes=bytes(uuid_bytes)),
            transaction_code=transaction_code,
            amount=50000,
            bank_name=bank_name,
            confidence=0.9,
            status=VerificationStatus.VERIFIED,
        )

    def test_check_all_layers(self):
        img_bytes = self.create_test_image("red")
        verification = self.create_verification("FT123456789", "MB Bank", "upload-1")

        results = self.detector.check_all(img_bytes, verification)

        assert len(results) == 3
        layers = [r.layer for r in results]
        assert "file_hash" in layers
        assert "perceptual_hash" in layers
        assert "transaction_identity" in layers

    def test_register_and_check(self):
        img_bytes = self.create_test_image("purple")
        verification = self.create_verification("FT999999999", "VPBank", "upload-new")

        self.detector.register(img_bytes, verification)

        results = self.detector.check_all(img_bytes, verification)
        assert any(r.is_duplicate for r in results)

    def test_load_existing(self):
        file_hashes = {hashlib.sha256(b"existing").hexdigest()}
        perceptual_hashes = {"abcdef1234567890": "upload-old"}
        transaction_identities = {"MB Bank|FT111111111": "upload-old"}

        self.detector.load_existing(file_hashes, perceptual_hashes, transaction_identities)

        img_bytes = self.create_test_image("red")
        verification = self.create_verification("FT111111111", "MB Bank", "upload-new")

        results = self.detector.check_all(img_bytes, verification)
        assert any(r.is_duplicate for r in results)
