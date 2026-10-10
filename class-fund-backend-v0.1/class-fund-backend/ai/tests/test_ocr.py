from unittest.mock import Mock, patch

import numpy as np
import pytest

from ai.ocr.service import (
    OCRService,
    Preprocessor,
    TesseractEngine,
    compute_file_hash,
    compute_perceptual_hash,
)


class TestPreprocessor:
    def setup_method(self):
        self.preprocessor = Preprocessor()
        self.test_image = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)

    def test_preprocess_default(self):
        result = self.preprocessor.preprocess(self.test_image, "default")
        assert result.strategy == "default"
        assert result.image is not None
        assert len(result.image.shape) == 2

    def test_preprocess_high_contrast(self):
        result = self.preprocessor.preprocess(self.test_image, "high_contrast")
        assert result.strategy == "high_contrast"
        assert result.image is not None

    def test_preprocess_denoise(self):
        result = self.preprocessor.preprocess(self.test_image, "denoise")
        assert result.strategy == "denoise"

    def test_preprocess_sharpen(self):
        result = self.preprocessor.preprocess(self.test_image, "sharpen")
        assert result.strategy == "sharpen"

    def test_preprocess_adaptive_threshold(self):
        result = self.preprocessor.preprocess(self.test_image, "adaptive_threshold")
        assert result.strategy == "adaptive_threshold"
        assert result.image.dtype == np.uint8

    def test_preprocess_morphology(self):
        result = self.preprocessor.preprocess(self.test_image, "morphology")
        assert result.strategy == "morphology"

    def test_preprocess_invalid_strategy_fallback(self):
        result = self.preprocessor.preprocess(self.test_image, "invalid_strategy")
        assert result.strategy == "default"

    def test_try_all_strategies(self):
        results = self.preprocessor.try_all_strategies(self.test_image)
        assert len(results) == len(self.preprocessor.strategies)
        for r in results:
            assert r.image is not None

    def test_resize_if_needed_small_image(self):
        small_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        resized = self.preprocessor._resize_if_needed(small_image, min_height=500)
        assert resized.shape[0] == 500

    def test_resize_if_needed_large_image(self):
        large_image = np.random.randint(0, 255, (2000, 1500), dtype=np.uint8)
        resized = self.preprocessor._resize_if_needed(large_image, min_height=1000)
        assert resized.shape[0] == 2000


class TestTesseractEngine:
    def setup_method(self):
        self.engine = TesseractEngine()

    @patch("ai.ocr.service.pytesseract.image_to_data")
    @patch("ai.ocr.service.pytesseract.image_to_string")
    @patch("ai.ocr.service.pytesseract.get_tesseract_version")
    def test_recognize(self, mock_version, mock_image_to_string, mock_image_to_data):
        mock_version.return_value = "5.3.0"
        mock_image_to_string.return_value = "Test OCR text\nLine 2"
        mock_image_to_data.return_value = {
            "text": ["Test", "OCR", "text", "Line", "2"],
            "conf": [90, 85, 88, 92, 90],
            "left": [10, 50, 90, 10, 50],
            "top": [10, 10, 10, 30, 30],
            "width": [30, 30, 30, 30, 20],
            "height": [20, 20, 20, 20, 20],
        }

        image = np.random.randint(0, 255, (200, 200), dtype=np.uint8)
        result = self.engine.recognize(image)

        assert result.raw_text == "Test OCR text\nLine 2"
        assert result.engine == "tesseract"
        assert result.engine_version == "5.3.0"
        assert len(result.lines) == 2
        assert result.confidence > 0

    def test_get_name(self):
        assert self.engine.get_name() == "tesseract"

    def test_get_version(self):
        with patch("ai.ocr.service.pytesseract.get_tesseract_version", return_value="5.3.0"):
            assert self.engine.get_version() == "5.3.0"


class TestOCRService:
    def setup_method(self):
        self.service = OCRService()

    def test_load_image_valid(self):
        import cv2
        image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".jpg", image)
        loaded = self.service._load_image(buffer.tobytes())
        assert loaded.shape == (200, 200, 3)

    def test_load_image_invalid(self):
        with pytest.raises(ValueError):
            self.service._load_image(b"invalid data")

    @patch.object(TesseractEngine, "recognize")
    def test_process_single_strategy(self, mock_recognize):
        mock_result = Mock()
        mock_result.confidence = 0.85
        mock_recognize.return_value = mock_result

        image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        import cv2
        _, buffer = cv2.imencode(".jpg", image)

        result = self.service.process(buffer.tobytes(), try_multiple=False)

        assert result == mock_result
        mock_recognize.assert_called_once()

    @patch.object(TesseractEngine, "recognize")
    def test_process_multiple_strategies(self, mock_recognize):
        mock_result1 = Mock()
        mock_result1.confidence = 0.7
        mock_result2 = Mock()
        mock_result2.confidence = 0.9
        mock_recognize.side_effect = [mock_result1, mock_result2, mock_result1, mock_result1, mock_result1, mock_result1]

        image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        import cv2
        _, buffer = cv2.imencode(".jpg", image)

        result = self.service.process(buffer.tobytes(), try_multiple=True)

        assert result.confidence == 0.9


class TestHashFunctions:
    def test_compute_file_hash(self):
        data = b"test image data"
        hash1 = compute_file_hash(data)
        hash2 = compute_file_hash(data)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_file_hash_different(self):
        hash1 = compute_file_hash(b"data1")
        hash2 = compute_file_hash(b"data2")
        assert hash1 != hash2

    def test_compute_perceptual_hash(self):
        import io

        from PIL import Image

        image = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        phash = compute_perceptual_hash(buffer.getvalue())
        assert len(phash) == 16
        assert all(c in "0123456789abcdef" for c in phash)

    def test_perceptual_hash_similar_images(self):
        import io

        from PIL import Image

        image1 = Image.new("RGB", (100, 100), color="red")
        buffer1 = io.BytesIO()
        image1.save(buffer1, format="PNG")

        image2 = Image.new("RGB", (100, 100), color="red")
        buffer2 = io.BytesIO()
        image2.save(buffer2, format="PNG")

        phash1 = compute_perceptual_hash(buffer1.getvalue())
        phash2 = compute_perceptual_hash(buffer2.getvalue())
        assert phash1 == phash2
